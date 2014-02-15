from django import forms
from django.contrib.auth.models import User
from django.core import mail
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from django.utils import timezone

from google.appengine.ext import testbed

import unicodecsv

from sjfnw.constants import TEST_MIDDLEWARE
from sjfnw.tests import BaseTestCase
from sjfnw.fund.models import GivingProject
from sjfnw.grants.forms import AppReportForm, OrgReportForm, AwardReportForm
from sjfnw.grants.models import GrantApplication, DraftGrantApplication, Organization, GrantCycle, GivingProjectGrant, SponsoredProgramGrant, ProjectApp

import datetime, json, unittest, logging
logger = logging.getLogger('sjfnw')


""" NOTE: some tests depend on having these files in sjfnw/media
  budget.docx      diversity.doc      funding_sources.docx
  budget1.docx     budget2.txt         budget3.png  """

LIVE_FIXTURES = ['sjfnw/fund/fixtures/live_gp_dump.json', #not using these yet in most
                 'sjfnw/grants/fixtures/orgs.json',
                 'sjfnw/grants/fixtures/grant_cycles.json',
                 'sjfnw/grants/fixtures/apps.json',
                 'sjfnw/grants/fixtures/drafts.json',
                 'sjfnw/grants/fixtures/project_apps.json',
                 'sjfnw/grants/fixtures/gp_grants.json']


class BaseGrantTestCase(BaseTestCase):
  """ Base for grants tests. Provides fixture and basic setUp
      as well as several helper functions """

  fixtures = ['sjfnw/grants/fixtures/test_grants.json']

  def logInNeworg(self):
    user = User.objects.create_user('neworg@gmail.com', 'neworg@gmail.com', 'noob')
    self.client.login(username = 'neworg@gmail.com', password = 'noob')

  def logInTestorg(self):
    user = User.objects.create_user('testorg@gmail.com', 'testorg@gmail.com', 'noob')
    self.client.login(username = 'testorg@gmail.com', password = 'noob')

  def setUp(self, login):
    super(BaseGrantTestCase, self).setUp(login)
    if login == 'testy':
      self.logInTestorg()
    elif login == 'newbie':
      self.logInNeworg()
    elif login == 'admin':
      self.logInAdmin()
    set_cycle_dates()

  class Meta:
    abstract = True


class BaseGrantFilesTestCase(BaseGrantTestCase):
  """ Can handle file uploads too """

  def setUp(self, login):
    super(BaseGrantFilesTestCase, self).setUp(login)
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    self.testbed.init_datastore_v3_stub()

  class Meta:
    abstract = True


def set_cycle_dates():
  """ Updates grant cycle dates to make sure they have the expected statuses:
      open, open, closed, upcoming, open """

  now = timezone.now()
  ten_days = datetime.timedelta(days=10)

  cycle = GrantCycle.objects.get(pk=1)
  cycle.open = now - ten_days
  cycle.close = now + ten_days
  cycle.save()
  twenty_days = datetime.timedelta(days=20)
  cycle = GrantCycle.objects.get(pk=2)
  cycle.open = now - ten_days
  cycle.close = now + ten_days
  cycle.save()
  cycle = GrantCycle.objects.get(pk=3)
  cycle.open = now - twenty_days
  cycle.close = now - ten_days
  cycle.save()
  cycle = GrantCycle.objects.get(pk=4)
  cycle.open = now + ten_days
  cycle.close = now + twenty_days
  cycle.save()
  cycle = GrantCycle.objects.get(pk=5)
  cycle.open = now - twenty_days
  cycle.close = now + ten_days
  cycle.save()
  cycle = GrantCycle.objects.get(pk=6)
  cycle.open = now - twenty_days
  cycle.close = now + ten_days
  cycle.save()


def alter_draft_timeline(draft, values):
  """ values: list of timeline widget values (0-14) """
  contents_dict = json.loads(draft.contents)
  for i in range(15):
    contents_dict['timeline_' + str(i)] = values[i]
  draft.contents = json.dumps(contents_dict)
  draft.save()


def alter_draft_files(draft, files_dict):
  """ File list should match this order:
      ['budget', 'demographics', 'funding_sources', 'budget1', 'budget2',
      'budget3', 'project_budget_file', 'fiscal_letter'] """
  files = dict(zip(DraftGrantApplication.file_fields(), files_dict))
  for key, val in files.iteritems():
    setattr(draft, key, val)
  draft.save()


def assert_app_matches_draft(self, draft, app, exclude_cycle): #only checks fields in draft
  """ Timeline formats:
        submitted: json'd list, in order, no file names
        draft: mixed in with other contents by widget name: timeline_0 - timeline_14 """
  draft_contents = json.loads(draft.contents)
  app_timeline = json.loads(app.timeline)
  for field, value in draft_contents.iteritems():
    if 'timeline' in field:
      i = int(field.split('_')[-1])
      self.assertEqual(value, app_timeline[i])
    else:
      self.assertEqual(value, getattr(app, field))
  for field in GrantApplication.file_fields():
    self.assertEqual(getattr(draft, field), getattr(app, field))
  if exclude_cycle:
    self.assertNotIn('cycle_question', draft_contents)


@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class Register(BaseGrantTestCase):

  url = reverse('sjfnw.grants.views.org_register')
  template_success = 'grants/org_home.html'
  template_error = 'grants/org_login_register.html'

  def setUp(self):
    super(Register, self).setUp('')

  def test_valid_registration(self):
    """ All fields provided, neither email nor name match an org in db """
    registration = {
      'email': 'uniquenewyork@gmail.com',
      'password': 'one',
      'passwordtwo': 'one',
      'organization': 'Unique, New York'
      }

    self.assertEqual(0, Organization.objects.filter(name='Unique, New York').count())
    self.assertEqual(0, User.objects.filter(email='uniquenewyork@gmail.com').count())

    response = self.client.post(self.url, registration, follow=True)

    self.assertEqual(1, Organization.objects.filter(name='Unique, New York').count())
    self.assertEqual(1, User.objects.filter(email='uniquenewyork@gmail.com').count())
    self.assertTemplateUsed(response, self.template_success)

  def test_repeat_org_name(self):
    """ Name matches an existing org (email doesn't) """
    registration = {
      'email': 'uniquenewyork@gmail.com',
      'password': 'one',
      'passwordtwo': 'one',
      'organization': 'officemax foundation'
      }

    self.assertEqual(1, Organization.objects.filter(name='OfficeMax Foundation').count())
    self.assertEqual(0, User.objects.filter(email='uniquenewyork@gmail.com').count())

    response = self.client.post(self.url, registration, follow=True)

    self.assertEqual(1, Organization.objects.filter(name='OfficeMax Foundation').count())
    self.assertEqual(0, User.objects.filter(email='uniquenewyork@gmail.com').count())
    self.assertTemplateUsed(response, self.template_error)
    self.assertFormError(response, 'register', None,
        'That organization is already registered. Log in instead.')

  def test_repeat_org_email(self):
    """ Email matches an existing org (name doesn't) """
    registration = {
      'email': 'neworg@gmail.com',
      'password': 'one',
      'passwordtwo': 'one',
      'organization': 'Brand New'
    }

    self.assertEqual(1, Organization.objects.filter(email='neworg@gmail.com').count())
    self.assertEqual(0, Organization.objects.filter(name='Brand New').count())

    response = self.client.post(self.url, registration, follow=True)

    self.assertEqual(1, Organization.objects.filter(email='neworg@gmail.com').count())
    self.assertEqual(0, Organization.objects.filter(name='Brand New').count())
    self.assertTemplateUsed(response, self.template_error)
    self.assertFormError(response, 'register', None,
        'That email is already registered. Log in instead.')

  def test_repeat_user_email(self):
    """ Email matches a user, but email/name don't match an org """
    User.objects.create_user('bababa@gmail.com', 'neworg@gmail.com', 'noob')

    registration = {
      'email': 'bababa@gmail.com',
      'password': 'one',
      'passwordtwo': 'one',
      'organization': 'Brand New'
      }

    self.assertEqual(1, User.objects.filter(email='neworg@gmail.com').count())
    self.assertEqual(0, Organization.objects.filter(name='Brand New').count())

    response = self.client.post(self.url, registration, follow=True)

    self.assertEqual(1, User.objects.filter(email='neworg@gmail.com').count())
    self.assertEqual(0, Organization.objects.filter(name='Brand New').count())
    self.assertTemplateUsed(response, self.template_error)
    self.assertFormError(response, 'register', None,
        'That email is registered with Project Central. Please register using a different email.')

  def test_admin_entered_match(self):
    """ Org name matches an org that was entered by staff (no login email) """

    org = Organization(name = "Ye olde Orge")
    org.save()

    registration = {
      'email': 'bababa@gmail.com',
      'password': 'one',
      'passwordtwo': 'one',
      'organization': 'Ye olde Orge'
    }

    response = self.client.post(self.url, registration, follow=True)

    org = Organization(name = "Ye olde Orge")
    # org email was updated
    #self.assertEqual(org.email, registration['email'])
    # user was created, is_active = False
    self.assertEqual(1, User.objects.filter(email='bababa@gmail.com', is_active=False).count())
    # stayed on login page
    self.assertTemplateUsed(response, self.template_error)
    # message telling them to contact admin
    self.assertMessage(response, ('You have registered successfully but your '
        'account needs administrator approval. Please contact '
        '<a href="mailto:info@socialjusticefund.org">info@socialjusticefund.org</a>'))

@override_settings(DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage',
    FILE_UPLOAD_HANDLERS = ('django.core.files.uploadhandler.MemoryFileUploadHandler',),
    MIDDLEWARE_CLASSES = TEST_MIDDLEWARE, MEDIA_ROOT = 'media/')
class ApplySuccessful(BaseGrantFilesTestCase):

  def setUp(self):
    super(ApplySuccessful, self).setUp('testy')

  def test_saved_timeline1(self):
    """ Verify that a timeline with just a complete first row is accepted

    Setup:
      Use same complete draft as test_post_valid_app
      Modify so just first row (first 3 entries of timeline) are filled in.

    Asserts:
      Gets newly created application (throws exception if not created)
      App timeline matches inputted timeline fields
    """

    answers = [ 'Jan', 'Chillin', 'Not applicable',
                '', '', '',
                '', '', '',
                '', '', '',
                '', '', '']

    draft = DraftGrantApplication.objects.get(organization_id = 2, grant_cycle_id = 3)
    alter_draft_timeline(draft, answers)

    response = self.client.post('/apply/3/', follow=True)
    self.assertEqual(response.status_code, 200)
    app = GrantApplication.objects.get(organization_id = 2, grant_cycle_id = 3) #TODO failing here
    self.assertEqual(app.timeline, json.dumps(answers))

  def test_saved_timeline5(self):
    """ Verify that a completely filled out timeline is accepted

    Setup:
      Use same complete draft as test_post_valid_app
      Modify draft with a fully filled out timeline

    Asserts:
      App created
      App timeline matches inputted values
    """

    answers = [
      'Jan', 'Chillin', 'Not applicable',
      'Feb', 'Petting dogs', '5 dogs',
      'Mar', 'Planting daffodils', 'Sprouts',
      'July', 'Walking around Greenlake', '9 times',
      'August', 'Reading in the shade', 'No sunburns',]

    draft = DraftGrantApplication.objects.get(organization_id = 2, grant_cycle_id = 3)
    alter_draft_timeline(draft, answers)

    response = self.client.post('/apply/3/', follow=True)
    self.assertEqual(response.status_code, 200)
    app = GrantApplication.objects.get(organization_id = 2, grant_cycle_id = 3)
    self.assertEqual(app.timeline, json.dumps(answers))

  def test_mult_budget(self):
    """ scenario: budget1, budget2, budget3

        verify: successful submission
                files match  """

    draft = DraftGrantApplication.objects.get(organization_id = 2, grant_cycle_id = 3)
    files = ['', 'funding_sources.docx', 'diversity.doc', 'budget1.docx', 'budget2.txt', 'budget3.png', '', '']
    alter_draft_files(draft, files)

    response = self.client.post('/apply/3/', follow=True)

    Organization.objects.get(pk=2)
    self.assertTemplateUsed(response, 'grants/submitted.html')
    app = GrantApplication.objects.get(organization_id = 2, grant_cycle_id = 3)
    self.assertEqual(0, DraftGrantApplication.objects.filter(organization_id = 2, grant_cycle_id = 3).count())
    self.assertEqual(app.budget1, files[3])
    self.assertEqual(app.budget2, files[4])
    self.assertEqual(app.budget, '')

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class ApplyBlocked(BaseGrantTestCase):

  def setUp(self):
    super(ApplyBlocked, self).setUp('testy')

  def test_closed_cycle(self):
    response = self.client.get('/apply/3/')
    self.assertTemplateUsed(response, 'grants/closed.html')

  def test_already_submitted(self):
    self.assertEqual(0, DraftGrantApplication.objects.filter(organization_id = 2, grant_cycle_id = 1).count())

    response = self.client.get('/apply/1/')

    self.assertTemplateUsed(response, 'grants/already_applied.html')
    self.assertEqual(0, DraftGrantApplication.objects.filter(organization_id = 2, grant_cycle_id = 1).count())

  def test_upcoming(self):
    response = self.client.get('/apply/4/')
    self.assertTemplateUsed(response, 'grants/closed.html')

  def test_nonexistent(self):
    response = self.client.get('/apply/79/')
    self.assertEqual(404, response.status_code)

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class ApplyValidation(BaseGrantFilesTestCase):
  """TO DO
      fiscal
      collab
      timeline
      files  """

  def setUp(self):
    super(ApplyValidation, self).setUp('testy')

  def test_project_requirements(self):
    """ scenario: support type = project, b1 & b2, no other project info given
        verify: not submitted
                no app created, draft still exists
                form errors - project title, project budget, project budget file """

    draft = DraftGrantApplication.objects.get(pk=2)
    contents_dict = json.loads(draft.contents)
    contents_dict['support_type'] = 'Project support'
    draft.contents = json.dumps(contents_dict)
    draft.save()

    response = self.client.post('/apply/3/', follow=True)

    self.assertTemplateUsed(response, 'grants/org_app.html')
    self.assertEqual(0, GrantApplication.objects.filter(organization_id = 2, grant_cycle_id = 3).count())
    self.assertEqual(1, DraftGrantApplication.objects.filter(organization_id = 2, grant_cycle_id = 3).count())
    self.assertFormError(response, 'form', 'project_title', "This field is required when applying for project support.")
    self.assertFormError(response, 'form', 'project_budget', "This field is required when applying for project support.")

  def test_timeline_incomplete(self):

    draft = DraftGrantApplication.objects.get(organization_id = 2, grant_cycle_id = 3)
    answers = [
      'Jan', 'Chillin', 'Not applicable',
      'Feb', 'Petting dogs', '5 dogs',
      'Mar', '', 'Sprouts',
      'July', '', '',
      '', 'Reading in the shade', 'No sunburns',]
    alter_draft_timeline(draft, answers)

    response = self.client.post('/apply/3/', follow=True)
    self.assertFormError(response, 'form', 'timeline', '<div class="form_error">All three columns are required for each quarter that you include in your timeline.</div>')

  def test_timeline_empty(self):

    draft = DraftGrantApplication.objects.get(organization_id = 2, grant_cycle_id = 3)
    answers = [
      '', '', '',
      '', '', '',
      '', '', '',
      '', '', '',
      '', '', '']
    alter_draft_timeline(draft, answers)

    response = self.client.post('/apply/3/', follow=True)
    self.assertFormError(response, 'form', 'timeline', '<div class="form_error">This field is required.</div>')

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class StartApplication(BaseGrantTestCase): #TODO MIGHT BE OUT OF DATE

  def setUp(self):
    super(StartApplication, self).setUp('none')

  def test_load_first_app(self):
    """ Brand new org starting an application
        Page loads
        Form is blank
        Draft is created """

    self.logInNeworg()
    self.assertEqual(0, DraftGrantApplication.objects.filter(organization_id=1, grant_cycle_id=1).count())

    response = self.client.get('/apply/1/')

    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, 'grants/org_app.html')
    self.assertEqual(1, DraftGrantApplication.objects.filter(organization_id=1, grant_cycle_id=1).count())

  def test_load_second_app(self):
    """ Org with profile starting an application
        Page loads
        Form has stuff from profile
        Draft is created """

    self.logInTestorg()
    self.assertEqual(0, DraftGrantApplication.objects.filter(organization_id=2, grant_cycle_id=6).count())

    response = self.client.get('/apply/6/')

    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, 'grants/org_app.html')
    org = Organization.objects.get(pk=2)
    self.assertContains(response, org.mission)
    self.assertEqual(1, DraftGrantApplication.objects.filter(organization_id=2, grant_cycle_id=6).count())

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class DraftWarning(BaseGrantTestCase):

  def setUp(self):
    super(DraftWarning, self).setUp('admin')

  def test_long_alert(self):
    """ Cycle created 12 days ago with cycle closing in 7.5 days """

    self.assertEqual(len(mail.outbox), 0)

    now = timezone.now()
    draft = DraftGrantApplication.objects.get(pk=1)
    draft.created = now - datetime.timedelta(days=12)
    draft.save()
    cycle = GrantCycle.objects.get(pk=2)
    cycle.close = now + datetime.timedelta(days=7, hours=12)
    cycle.save()

    self.client.get('/mail/drafts/')
    self.assertEqual(len(mail.outbox), 1)

  def test_long_alert_skip(self):
    """ Cycle created now with cycle closing in 7.5 days """

    self.assertEqual(len(mail.outbox), 0)

    now = timezone.now()
    draft = DraftGrantApplication.objects.get(pk=1)
    draft.created = now
    draft.save()
    cycle = GrantCycle.objects.get(pk=2)
    cycle.close = now + datetime.timedelta(days=7, hours=12)
    cycle.save()

    self.client.get('/mail/drafts/')
    self.assertEqual(len(mail.outbox), 0)

  def test_short_alert(self):
    """ Cycle created now with cycle closing in 2.5 days """

    self.assertEqual(len(mail.outbox), 0)

    now = timezone.now()
    draft = DraftGrantApplication.objects.get(pk=1)
    draft.created = now
    draft.save()
    cycle = GrantCycle.objects.get(pk=2)
    cycle.close = now + datetime.timedelta(days=2, hours=12)
    cycle.save()

    self.client.get('/mail/drafts/')
    self.assertEqual(len(mail.outbox), 1)

  def test_short_alert_ignore(self):
    """ Cycle created 12 days ago with cycle closing in 2.5 days """
    self.assertEqual(len(mail.outbox), 0)

    now = timezone.now()
    draft = DraftGrantApplication.objects.get(pk=1)
    draft.created = now - datetime.timedelta(days=12)
    draft.save()
    cycle = GrantCycle.objects.get(pk=2)
    cycle.close = now + datetime.timedelta(days=2, hours=12)
    cycle.save()

    self.client.get('/mail/drafts/')
    self.assertEqual(len(mail.outbox), 0)

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class OrgRollover(BaseGrantTestCase):
  """ Basic success
  content,   timeline,   files,   not extra cycle q   """

  def setUp(self, *args):
    super(OrgRollover, self).setUp('newbie')

  def test_draft_rollover(self):
    """ scenario: take complete draft, make it belong to new org, rollover to cycle 1
        verify:
          success (status code & template)
          new draft created
          new draft contents = old draft contents (ignoring cycle q)
          new draft files = old draft files  """

    draft = DraftGrantApplication.objects.get(organization_id = 2, grant_cycle_id = 3)
    draft.organization = Organization.objects.get(pk=1)
    draft.save()
    self.assertEqual(0, DraftGrantApplication.objects.filter(organization_id=1, grant_cycle_id=1).count())

    response = self.client.post('/apply/copy',
        {'cycle':'1', 'draft':'2', 'application':''}, follow=True)

    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, 'grants/org_app.html')
    self.assertEqual(1, DraftGrantApplication.objects.filter(organization_id=1, grant_cycle_id=1).count())
    new_draft = DraftGrantApplication.objects.get(organization_id = 1, grant_cycle_id = 1)
    old_contents = json.loads(draft.contents) # TODO could this use the compare function defined in base?
    old_cycle_q = old_contents.pop('cycle_question', None)
    new_contents = json.loads(new_draft.contents)
    new_cycle_q = new_contents.pop('cycle_question', '')
    self.assertEqual(old_contents, new_contents)
    self.assertNotEqual(old_cycle_q, new_cycle_q)
    for field in GrantApplication.file_fields():
      self.assertEqual(getattr(draft, field), getattr(new_draft, field))

  def test_app_rollover(self):
    """ scenario: take a submitted app, make it belong to new org, rollover to cycle 1
        verify:
          success (status code & template)
          new draft created
          draft contents = app contents (ignoring cycle q)
          draft files = app files  """

    self.assertEqual(0, DraftGrantApplication.objects.filter(organization_id=1, grant_cycle_id=2).count())

    app = GrantApplication.objects.get(organization_id=2, grant_cycle_id=1)
    app.organization = Organization.objects.get(pk=1)
    app.save()

    response = self.client.post('/apply/copy', {'cycle':'2', 'draft':'', 'application':'1'}, follow=True)

    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, 'grants/org_app.html')
    self.assertEqual(1, DraftGrantApplication.objects.filter(organization_id=1, grant_cycle_id=2).count())

    draft = DraftGrantApplication.objects.get(organization_id=1, grant_cycle_id=2)
    assert_app_matches_draft(self, draft, app, True)

  def test_rollover_form_display(self):
    """ Verify that rollover form displays correctly for both orgs

    cycle_count = number of open cycles that don't have a draft or app already
    apps_count = number of drafts + number of apps
    (+1 are for the starting option)
    """
    # start out logged into neworg
    response = self.client.get('/apply/copy')
    self.assertTemplateUsed(response, 'grants/org_app_copy.html')
    self.assertEqual(response.context['apps_count'], 0)
    self.assertEqual(response.context['cycle_count'], 4)
    self.assertNotContains(response, 'Select')
    self.client.logout()
    # login to testorg (officemax)
    self.logInTestorg()
    response = self.client.get('/apply/copy')
    self.assertTemplateUsed(response, 'grants/org_app_copy.html')
    self.assertEqual(response.context['apps_count'], 4)
    self.assertEqual(response.context['cycle_count'], 1)
    self.assertContains(response, 'Select')

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class AdminRevert(BaseGrantTestCase):

  def setUp(self):
    super(AdminRevert, self).setUp('admin')

  def test_load_revert(self):

    response = self.client.get('/admin/grants/grantapplication/1/revert')

    self.assertEqual(200, response.status_code)
    self.assertContains(response, 'Are you sure you want to revert this application into a draft?')

  def test_revert_app(self):
    """ scenario: revert submitted app pk1
        verify:
          draft created
          app gone
          draft fields match app (incl cycle, timeline) """

    self.assertEqual(0, DraftGrantApplication.objects.filter(organization_id=2, grant_cycle_id=1).count())
    app = GrantApplication.objects.get(organization_id=2, grant_cycle_id=1)

    response = self.client.post('/admin/grants/grantapplication/1/revert')

    self.assertEqual(1, DraftGrantApplication.objects.filter(organization_id=2, grant_cycle_id=1).count())
    draft = DraftGrantApplication.objects.get(organization_id=2, grant_cycle_id=1)
    assert_app_matches_draft(self, draft, app, False)

@unittest.skip('Incomplete')
@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class AdminRollover(BaseGrantTestCase):

  def setUp(self):
    super(AdminRollover, self).setUp('admin')

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class DraftExtension(BaseGrantTestCase):

  def setUp(self):
    super(DraftExtension, self).setUp('admin')

  def test_create_draft(self):
    """ Admin create a draft for Fresh New Org """

    self.assertEqual(0, DraftGrantApplication.objects.filter(organization_id=1).count())

    response = self.client.post('/admin/grants/draftgrantapplication/add/',
                                {'organization': '1', 'grant_cycle': '3',
                                 'extended_deadline_0': '2013-04-07',
                                 'extended_deadline_1': '11:19:46'})

    self.assertEqual(response.status_code, 302)
    new = DraftGrantApplication.objects.get(organization_id=1) #in effect, asserts 1 draft
    self.assertTrue(new.editable)
    self.assertIn('/admin/grants/draftgrantapplication/', response.__getitem__('location'), )

  @unittest.skip('Incomplete')
  def test_org_drafts_list(self):
    pass

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class Draft(BaseGrantTestCase):

  def setUp(self):
    super(Draft, self).setUp('testy')

  def test_autosave1(self):
    """ scenario: steal contents of draft 2, turn it into a dict. submit that as request.POST for cycle 5
        verify: draft contents match  """
    complete_draft = DraftGrantApplication.objects.get(pk=2)
    new_draft = DraftGrantApplication(organization = Organization.objects.get(pk=2), grant_cycle = GrantCycle.objects.get(pk=5))
    new_draft.save()
    dic = json.loads(complete_draft.contents)
    #fake a user id like the js would normally do
    dic['user_id'] = 'asdFDHAF34qqhRHFEA'
    self.maxDiff = None

    response = self.client.post('/apply/5/autosave/', dic)
    self.assertEqual(200, response.status_code)
    new_draft = DraftGrantApplication.objects.get(organization_id=2, grant_cycle_id=5)
    new_c = json.loads(new_draft.contents)
    del new_c['user_id']
    self.assertEqual(json.loads(complete_draft.contents), new_c)

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class ViewGrantPermissions(BaseGrantTestCase):

  fixtures = ['sjfnw/grants/fixtures/test_grants.json', 'sjfnw/fund/fixtures/test_fund.json']

  def setUp(self):
    pa = ProjectApp(application_id = 1, giving_project_id = 2)
    pa.save()

  """ Note: using grant app #1
    Author: testorg@gmail.com (org #2)
    GP: #2, which newacct is a member of, test is not
  """
  def test_author(self):
    self.logInTestorg()

    response = self.client.get('/grants/view/1', follow=True)

    self.assertTemplateUsed(response, 'grants/reading.html')
    self.assertEqual(3, response.context['perm'])

  def test_other_org(self):
    self.logInNeworg()

    response = self.client.get('/grants/view/1', follow=True)

    self.assertTemplateUsed(response, 'grants/reading.html')
    self.assertEqual(0, response.context['perm'])

  def test_staff(self):
    self.logInAdmin()

    response = self.client.get('/grants/view/1', follow=True)

    self.assertTemplateUsed(response, 'grants/reading.html')
    self.assertEqual(2, response.context['perm'])

  def test_valid_member(self):
    self.logInNewbie()

    response = self.client.get('/grants/view/1', follow=True)

    self.assertTemplateUsed(response, 'grants/reading.html')
    self.assertEqual(1, response.context['perm'])

  def test_invalid_member(self):
    self.logInTesty()

    response = self.client.get('/grants/view/1', follow=True)

    self.assertTemplateUsed(response, 'grants/reading.html')
    self.assertEqual(0, response.context['perm'])

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class OrgHomeAwards(BaseGrantTestCase):
  """ Verify that correct data is showing on the org home page """

  url = reverse('sjfnw.grants.views.org_home')
  template = 'grants/org_home.html'

  def setUp(self):
    super(OrgHomeAwards, self).setUp('testy')

  #TODO test mult awards per app

  def test_none(self):
    """ org has no awards. verify no award info is shown """

    response = self.client.get(self.url)

    self.assertTemplateUsed(response, self.template)
    self.assertNotContains(response, 'Agreement mailed')

  def test_early(self):
    """ org has an award, but agreement has not been mailed. verify not shown """
    award = GivingProjectGrant(project_app_id = 1, amount = 9000)
    award.save()

    response = self.client.get(self.url)

    self.assertTemplateUsed(response, self.template)
    self.assertNotContains(response, 'Agreement mailed')

  def test_sent(self):
    """ org has award, agreement mailed. verify shown """
    award = GivingProjectGrant(project_app_id = 1, amount = 9000,
        agreement_mailed = timezone.now()-datetime.timedelta(days=1))
    award.save()

    response = self.client.get(self.url)

    self.assertTemplateUsed(response, self.template)
    self.assertContains(response, 'Agreement mailed')

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class Reporting(BaseGrantTestCase):
  """ Admin reporting on applications, awards and organizations

  Fields can just be tested once; filters should be tested in combinations
  Fixtures include unicode characters
  """

  fixtures = LIVE_FIXTURES
  url = reverse('sjfnw.grants.views.grants_report')
  template_success = 'grants/report_results.html'
  template_error = 'grants/reporting.html'

  def setUp(self): #don't super, can't set cycle dates with this fixture
    self.logInAdmin()

  def fill_report_form(self, form, filters=False, fields=False, fmt='browse'):
    """ Shared method to create POST data for the given form

    Methods need to insert report type key themselves
    Set up to handle:
      boolean
      select fields
      year min & max
      organization_name & city (all other chars are blank)

    Args:
      form: form instance to populate
      filters: True = select all filters, False = select none
      fields: True = select all fields, TODO False = select none
      fmt: browse or csv option in form

    Returns:
      Dictionary that should be a valid POST submission for the given form
    """

    post_dict = {}
    for bfield in form:
      field = bfield.field
      name = bfield.name
      # fields
      if fields and name.startswith('report'):
        if isinstance(field, forms.BooleanField):
          post_dict[name] = True
        elif isinstance(field, forms.MultipleChoiceField):
          post_dict[name] = [val[0] for val in field.choices]
        else:
          logger.error('Unexpected field type: ' + str(field))
      # filters
      else:
        if isinstance(field, forms.BooleanField):
          post_dict[name] = True if filters else False
        elif isinstance(field, forms.MultipleChoiceField):
          post_dict[name] = [field.choices[0][0], field.choices[1][0]] if filters else []
        elif name.startswith('year_m'):
          if name == 'year_min':
            post_dict[name] = 1995
          else:
            post_dict[name] = timezone.now().year
        elif isinstance(field, forms.CharField):
          if filters:
            if name == 'organization_name':
              post_dict[name] = 'Foundation'
            elif name == 'city':
              post_dict[name] = 'Seattle'
          else:
            post_dict[name] = ''
        elif name == 'registered':
          post_dict[name] = True if filters else None
        else:
          logger.warning('Unexpected field type: ' + str(field))

    post_dict['format'] = fmt
    return post_dict


  def test_app_fields(self):
    """ Verify that application fields are fetched for browsing without error

    Setup:
      No filters selected
      All fields selected
      Format = browse

    Asserts:
      Basic success: 200 status, correct template
      Number of rows in results == number of apps in database

    """

    form = AppReportForm()
    post_dict = self.fill_report_form(form, fields=True)
    post_dict['run-application'] = '' # simulate dropdown at top of page

    response = self.client.post(self.url, post_dict)

    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, self.template_success)

    results = response.context['results']
    self.assertEqual(len(results), GrantApplication.objects.count())

  def test_app_fields_csv(self):
    """ Verify that application fields are fetched in csv format without error

    Setup:
      No filters selected
      All fields selected
      Format = csv

    Asserts:
      Basic success: able to iterate through response with reader
      Number of rows in results matches number of apps in database
    """

    form = AppReportForm()
    post_dict = self.fill_report_form(form, fields=True, fmt='csv')
    post_dict['run-application'] = '' # simulate dropdown at top of page

    response = self.client.post(self.url, post_dict)

    reader = unicodecsv.reader(response, encoding = 'utf8')
    row_count = sum(1 for row in reader)
    # 1st row is blank, 2nd is headers
    self.assertEqual(row_count-2, GrantApplication.objects.count())

  def test_app_filters_all(self):
    """ Verify that all filters can be selected without error

    Setup:
      All fields
      All filters
      Format = browse

    Asserts:
      Basic success: 200 status, correct template
      Number of rows in results == number of apps in database
    """

    form = AppReportForm()
    post_dict = self.fill_report_form(form, fields=True, filters=True)
    post_dict['run-application'] = ''

    response = self.client.post(self.url, post_dict)

    self.assertEqual(200, response.status_code)
    self.assertTemplateUsed(response, self.template_success)

    results = response.context['results']
    self.assertEqual(results, [])

  def test_award_fields(self):
    """ Verify that award fields can be fetched

    Setup:
      No filters selected
      All fields selected
      Format = browse

    Asserts:
      Basic success: 200 status, correct template
      Number of rows in results == number of awards (gp + sponsored) in db
    """

    form = AwardReportForm()
    post_dict = self.fill_report_form(form, fields=True)
    post_dict['run-award'] = ''

    response = self.client.post(self.url, post_dict)

    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, self.template_success)

    results = response.context['results']
    self.assertEqual(len(results),
        GivingProjectGrant.objects.count() + SponsoredProgramGrant.objects.count())

  def test_award_fields_csv(self):
    """ Verify that award fields can be fetched in csv format

    Setup:
      No filters selected
      All fields selected
      Format = browse

    Asserts:
      Basic success: able to iterate through response with reader
      Number of rows in results matches number of awards (gp + sponsored) in db

    """

    form = AwardReportForm()
    post_dict = self.fill_report_form(form, fields=True, fmt='csv')
    post_dict['run-award'] = ''

    response = self.client.post(self.url, post_dict)

    reader = unicodecsv.reader(response, encoding = 'utf8')
    row_count = sum(1 for row in reader)
    self.assertEqual(row_count-2,
        GivingProjectGrant.objects.count() + SponsoredProgramGrant.objects.count())

  def test_award_filters_all(self):
    """ Verify that all filters can be selected in award report without error

    Setup:
      All fields
      All filters
      Format = browse

    Asserts:
      Basic success: 200 status, correct template
    """

    form = AwardReportForm()
    post_dict = self.fill_report_form(form, fields=True, filters=True)
    post_dict['run-award'] = ''

    response = self.client.post(self.url, post_dict)

    self.assertEqual(200, response.status_code)
    self.assertTemplateUsed(response, self.template_success)

    results = response.context['results']
    logger.info(results)

  def test_org_fields(self):
    """ Verify that org fields can be fetched

    Setup:
      No filters selected
      All fields selected
      Format = browse

    Asserts:
      Basic success: 200 status, correct template
      Number of rows in results == number of organizations in db
    """

    form = OrgReportForm()
    post_dict = self.fill_report_form(form, fields=True)
    post_dict['run-organization'] = ''

    response = self.client.post(self.url, post_dict)

    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, self.template_success)

    results = response.context['results']
    self.assertEqual(len(results), Organization.objects.count())

  def test_org_fields_csv(self):
    """ Verify that org fields can be fetched in csv format

    Setup:
      No filters selected
      All fields selected
      Format = browse

    Asserts:
      Basic success: able to iterate through response with reader
      Number of rows in results matches number of orgs in db

    """

    form = OrgReportForm()
    post_dict = self.fill_report_form(form, fields=True, fmt='csv')
    post_dict['run-organization'] = ''

    response = self.client.post(self.url, post_dict)

    reader = unicodecsv.reader(response, encoding = 'utf8')
    row_count = sum(1 for row in reader)
    self.assertEqual(row_count-2, Organization.objects.count())

  def test_org_filters_all(self):
    """ Verify that all filters can be selected in org report without error

    Setup:
      All fields
      All filters
      Format = browse

    Asserts:
      Basic success: 200 status, correct template
    """

    form = OrgReportForm()
    post_dict = self.fill_report_form(form, fields=True, filters=True)
    post_dict['run-organization'] = ''

    response = self.client.post(self.url, post_dict)

    self.assertEqual(200, response.status_code)
    self.assertTemplateUsed(response, self.template_success)

    results = response.context['results']
    self.assertEqual(0, len(results))


@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class AdminInlines(BaseGrantTestCase):
  """ Verify basic display of related inlines for grants objects in admin """

  fixtures = LIVE_FIXTURES

  def setUp(self): #don't super, can't set cycle dates with this fixture
    self.logInAdmin()

  def test_organization(self):
    """ Verify that related inlines show existing objs

    Setup:
      Log in as admin, go to org #
      Orgs 41, 154, 156 have application, draft, gp grant

    Asserts:
      Application inline
    """

    organization = Organization.objects.get(pk=41)

    app = organization.grantapplication_set.all()[0]

    response = self.client.get('/admin/grants/organization/41/')

    self.assertContains(response, app.grant_cycle.title)
    self.assertContains(response, app.pre_screening_status)

  def test_givingproject(self):
    """ Verify that assigned grant applications (projectapps) are shown as inlines

    Setup:
      Find a GP that has projectapps

    Asserts:
      Displays one of the assigned apps
    """

    apps = ProjectApp.objects.filter(giving_project_id=19)

    response = self.client.get('/admin/fund/givingproject/19/')

    self.assertContains(response, 'selected="selected">' + str(apps[0].application))

  def test_application(self):
    """ Verify that gp assignment and awards are shown on application page

    Setup:
      Use application with GP assignment. App 274, Papp 3

    Asserts:
      ASSERTIONS
    """

    papp = ProjectApp.objects.get(pk=3)

    response = self.client.get('/admin/grants/grantapplication/274/')

    self.assertContains(response, papp.giving_project.title)
    self.assertContains(response, papp.screening_status)

