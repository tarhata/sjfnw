from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone
from django.utils.html import strip_tags
from google.appengine.ext import testbed
from models import GrantApplication, DraftGrantApplication, Organization, GrantCycle
import sys, datetime, re, json, unittest
from sjfnw.constants import TEST_MIDDLEWARE, APP_FILE_FIELDS

def setCycleDates():
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

def logInTesty(self): # 2 OfficeMax Foundation
  self.user = User.objects.create_user('testacct@gmail.com', 'testacct@gmail.com', 'testy')
  self.client.login(username = 'testacct@gmail.com', password = 'testy')

def logInNewbie(self): # 1 Fresh New Org
  user = User.objects.create_user('newacct@gmail.com', 'newacct@gmail.com', 'noob')
  self.client.login(username = 'newacct@gmail.com', password = 'noob')

def logInAdmin(self): #just a django superuser
  superuser = User.objects.create_superuser('admin@gmail.com', 'admin@gmail.com', 'admin')
  self.client.login(username = 'admin@gmail.com', password = 'admin')

def alterDraftTimeline(draft, values):
  contents_dict = json.loads(draft.contents)
  for i in range(15):
    contents_dict['timeline_' + str(i)] = values[i]
  draft.contents = json.dumps(contents_dict)
  draft.save()

def alterDraftFiles(draft, files_dict):
  files = dict(zip(APP_FILE_FIELDS, files_dict))
  for key, val in files.iteritems():
    setattr(draft, key, val)
  draft.save()

def assertDraftAppMatch(self, draft, app, exclude_cycle): #only checks fields in draft
  draft_contents = json.loads(draft.contents)
  app_timeline = json.loads(app.timeline)
  for field, value in draft_contents.iteritems():
    if 'timeline' in field:
      i = int(field.split('_')[-1])
      self.assertEqual(value, app_timeline[i])
    else:
      self.assertEqual(value, getattr(app, field))
  for field in APP_FILE_FIELDS:
    self.assertEqual(getattr(draft, field), getattr(app, field))
  if exclude_cycle:
    self.assertNotIn('cycle_question', draft_contents)

#@unittest.skip('Not right now')
@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class ApplySuccessfulTests(TestCase):
  
  """ TODO: apply with deadline extension """

  fixtures = ['test_grants.json',] 
  
  def setUp(self):
    setCycleDates()
    logInTesty(self)
  
  @override_settings(DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage', MEDIA_ROOT = 'media/', FILE_UPLOAD_HANDLERS = ('django.core.files.uploadhandler.MemoryFileUploadHandler',))
  def test_post_valid_app(self):
    """ scenario: start with a complete draft, post to apply
                  general, no fiscal, all-in-one budget

        verify: response is success page
                grantapplication created
                draft deleted
                email sent
                org profile updated """

    org = Organization.objects.get(pk = 2)
    self.assertEqual(0, GrantApplication.objects.filter(organization_id = 2, grant_cycle_id = 3).count())
    self.assertEqual(1, DraftGrantApplication.objects.filter(organization_id = 2, grant_cycle_id = 3).count())   
    self.assertEqual(org.mission, 'Some crap')
    
    response = self.client.post('/apply/3/', follow=True)
    
    #form = response.context['form']
    #print(form.errors)
    org = Organization.objects.get(pk = 2)
    self.assertTemplateUsed(response, 'grants/submitted.html')
    self.assertEqual(org.mission, u'Our mission is to boldly go where no database has gone before.')
    self.assertEqual(1, GrantApplication.objects.filter(organization_id = 2, grant_cycle_id = 3).count())
    self.assertEqual(0, DraftGrantApplication.objects.filter(organization_id = 2, grant_cycle_id = 3).count())
  
  def test_saved_timeline1(self):

    answers = [
      'Jan', 'Chillin', 'Not applicable',
      '', '', '',
      '', '', '',
      '', '', '',
      '', '', '',]
    
    draft = DraftGrantApplication.objects.get(organization_id = 2, grant_cycle_id = 3)
    alterDraftTimeline(draft, answers)
    
    response = self.client.post('/apply/3/', follow=True)
    self.assertEqual(response.status_code, 200)
    app = GrantApplication.objects.get(organization_id = 2, grant_cycle_id = 3)
    self.assertEqual(app.timeline, json.dumps(answers))
   
  def test_saved_timeline5(self):

    answers = [
      'Jan', 'Chillin', 'Not applicable',
      'Feb', 'Petting dogs', '5 dogs',
      'Mar', 'Planting daffodils', 'Sprouts',
      'July', 'Walking around Greenlake', '9 times',
      'August', 'Reading in the shade', 'No sunburns',]
    
    draft = DraftGrantApplication.objects.get(organization_id = 2, grant_cycle_id = 3)
    alterDraftTimeline(draft, answers)
    
    response = self.client.post('/apply/3/', follow=True)
    self.assertEqual(response.status_code, 200)
    app = GrantApplication.objects.get(organization_id = 2, grant_cycle_id = 3)
    self.assertEqual(app.timeline, json.dumps(answers))
  
  @override_settings(DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage', MEDIA_ROOT = 'media/', FILE_UPLOAD_HANDLERS = ('django.core.files.uploadhandler.MemoryFileUploadHandler',))
  def test_mult_budget(self):
    """ scenario: budget1, budget2
              
        verify: successful submission
                files match  """
                
    draft = DraftGrantApplication.objects.get(organization_id = 2, grant_cycle_id = 3)
    files = ['', 'diversity_chart.doc', 'diversity_chart.doc', '', 'fileuploads3.png', 'notes.txt', '', '']
    alterDraftFiles(draft, files)
    response = self.client.post('/apply/3/', follow=True)
    
    org = Organization.objects.get(pk = 2)
    self.assertTemplateUsed(response, 'grants/submitted.html')
    app = GrantApplication.objects.get(organization_id = 2, grant_cycle_id = 3)
    self.assertEqual(0, DraftGrantApplication.objects.filter(organization_id = 2, grant_cycle_id = 3).count())
    self.assertEqual(app.budget1, files[4])
    self.assertEqual(app.budget2, files[5])
    self.assertEqual(app.budget, '')

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class ApplyBlockedTests(TestCase):
 
  fixtures = ['test_grants.json',]   
  def setUp(self):
    setCycleDates()
    logInTesty(self)

  def test_closed_cycle(self):
    response = self.client.get('/apply/3/')
    self.assertTemplateUsed('grants/closed.html')
  
  def test_already_submitted(self):
    self.assertEqual(0, DraftGrantApplication.objects.filter(organization_id = 2, grant_cycle_id = 1).count())
    
    response = self.client.get('/apply/1/')
    
    self.assertTemplateUsed('grants/already-applied.html')
    self.assertEqual(0, DraftGrantApplication.objects.filter(organization_id = 2, grant_cycle_id = 1).count())
  
  def test_upcoming(self):
    response = self.client.get('/apply/4/')
    self.assertTemplateUsed('grants/closed.html')
  
  def test_nonexistent(self):
    response = self.client.get('/apply/79/')
    self.assertEqual(404, response.status_code)

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class ApplyValidationTests(TestCase):
  """TO DO
      fiscal
      collab
      timeline
      files  """
  
  fixtures = ['test_grants.json',]   
  def setUp(self):
    setCycleDates()
    logInTesty(self)
  
  def test_file_validation_budget(self):
    """ scenario: budget + some other budget files
                  no funding sources
                  
        verify: no submission
                error response  """
    draft = DraftGrantApplication.objects.get(organization_id = 2, grant_cycle_id = 3)
    files = ['budget.doc', 'diversity_chart.doc', '', '', 'fileuploads3.png', 'notes.txt', '', '']
    alterDraftFiles(draft, files)
    response = self.client.post('/apply/3/', follow=True)
    
    self.assertTemplateUsed(response, 'grants/org_app.html')
    self.assertEqual(0, GrantApplication.objects.filter(organization_id = 2, grant_cycle_id = 3).count())
    self.assertEqual(1, DraftGrantApplication.objects.filter(organization_id = 2, grant_cycle_id = 3).count())
    self.assertFormError(response, 'form', 'funding_sources', "This field is required.")
    self.assertFormError(response, 'form', 'budget', "Budget documents should be uploaded all in one file OR in the individual fields below.")
  
  def test_project_requirements(self):
    """ scenario: support type = project, b1 & b2, no other project info given
        verify: not submitted
                no app created, draft still exists
                form errors - project title, project budget, project budget file """
                
    draft = DraftGrantApplication.objects.get(organization_id = 2, grant_cycle_id = 3)
    contents_dict = json.loads(draft.contents)
    contents_dict['support_type'] = 'Project support'
    draft.contents = json.dumps(contents_dict)
    files = ['', 'diversity_chart.doc', 'diversity_chart.doc', '', 'fileuploads3.png', 'notes.txt', '', '']
    alterDraftFiles(draft, files)
    
    response = self.client.post('/apply/3/', follow=True)
    self.assertTemplateUsed(response, 'grants/org_app.html')
    self.assertEqual(0, GrantApplication.objects.filter(organization_id = 2, grant_cycle_id = 3).count())
    self.assertEqual(1, DraftGrantApplication.objects.filter(organization_id = 2, grant_cycle_id = 3).count())
    self.assertFormError(response, 'form', 'project_title', "This field is required when applying for project support.")
    self.assertFormError(response, 'form', 'project_budget', "This field is required when applying for project support.")
    self.assertFormError(response, 'form', 'project_budget_file', "This field is required when applying for project support.")
  
  def test_timeline_validation1(self):
    
    draft = DraftGrantApplication.objects.get(organization_id = 2, grant_cycle_id = 3)
    answers = [
      'Jan', 'Chillin', 'Not applicable',
      'Feb', 'Petting dogs', '5 dogs',
      'Mar', '', 'Sprouts',
      'July', '', '',
      '', 'Reading in the shade', 'No sunburns',]
    alterDraftTimeline(draft, answers)
    
    response = self.client.post('/apply/3/', follow=True)
    self.assertFormError(response, 'form', 'timeline', '<div class="form_error">All three columns are required for each quarter that you include in your timeline.</div>')
    
  def test_timeline_validation1(self):
    
    draft = DraftGrantApplication.objects.get(organization_id = 2, grant_cycle_id = 3)
    answers = [
      '', '', '',
      '', '', '',
      '', '', '',
      '', '', '',
      '', '', '']
    alterDraftTimeline(draft, answers)
    
    response = self.client.post('/apply/3/', follow=True)
    self.assertFormError(response, 'form', 'timeline', '<div class="form_error">This field is required.</div>')

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)    
class StartApplicationTests(TestCase): #MIGHT BE OUT OF DATE
  
  fixtures = ['test_grants.json',]  
  def setUp(self):
    setCycleDates()

  def test_load_first_app(self):
    """ Brand new org starting an application
        Page loads
        Form is blank
        Draft is created """

    logInNewbie(self)
    self.assertEqual(0, DraftGrantApplication.objects.filter(organization_id=1, grant_cycle_id=1).count())
     
    response = self.client.get('/apply/1/')
    
    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed('grants/org_app.html')
    self.assertEqual(1, DraftGrantApplication.objects.filter(organization_id=1, grant_cycle_id=1).count())

  def test_load_second_app(self):
    """ Org with profile starting an application
        Page loads
        Form has stuff from profile
        Draft is created """
        
    logInTesty(self)
    self.assertEqual(0, DraftGrantApplication.objects.filter(organization_id=2, grant_cycle_id=5).count())
     
    response = self.client.get('/apply/5/')
    
    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed('grants/org_app.html')
    org = Organization.objects.get(pk=2)
    self.assertContains(response, org.mission)
    self.assertEqual(1, DraftGrantApplication.objects.filter(organization_id=2, grant_cycle_id=5).count())

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class DraftWarningTests(TestCase):
  
  fixtures = ['test_grants.json',]
  def setUp(self):
    logInAdmin(self)
    setCycleDates()
  
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
    
    response = self.client.get('/mail/drafts/')
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
    
    response = self.client.get('/mail/drafts/')
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
    
    response = self.client.get('/mail/drafts/')
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
    
    response = self.client.get('/mail/drafts/')
    self.assertEqual(len(mail.outbox), 0)
  
@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class RolloverTests(TestCase):
  """ Basic success
  content,   timeline,   files,   not extra cycle q   """
  
  fixtures = ['test_grants.json',]
  def setUp(self):
    setCycleDates()
    logInNewbie(self)
  
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
    
    response = self.client.post('/apply/copy', {'cycle':'1', 'draft':'2', 'application':''}, follow=True)
    
    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, 'grants/org_app.html')
    self.assertEqual(1, DraftGrantApplication.objects.filter(organization_id=1, grant_cycle_id=1).count())
    new_draft = DraftGrantApplication.objects.get(organization_id = 1, grant_cycle_id = 1)
    old_contents = json.loads(draft.contents)
    cq = old_contents.pop('cycle_question', None)
    new_contents = json.loads(new_draft.contents)
    nq = new_contents.pop('cycle_question', '')
    self.assertEqual(old_contents, new_contents)
    self.assertNotEqual(cq, nq)
    for field in APP_FILE_FIELDS:
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
    assertDraftAppMatch(self, draft, app, True)

  def test_rollover_form_display(self):
    response = self.client.get('/apply/copy')
    self.assertTemplateUsed(response, 'grants/org_app_copy.html')
    self.assertEqual(response.context['apps_count'], 2)
    self.assertEqual(response.context['cycle_count'], 4)
    self.assertNotContains(response, 'Select')
    
    self.client.logout()
    logInTesty(self)
    response = self.client.get('/apply/copy')
    self.assertTemplateUsed(response, 'grants/org_app_copy.html')
    self.assertEqual(response.context['apps_count'], 5)
    self.assertEqual(response.context['cycle_count'], 2)
    self.assertContains(response, 'Select')

@unittest.skip('Not done with revert yet')      
@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class RevertTests(TestCase):
  
  fixtures = ['test_grants.json',]
  
  def setUp(self):
    setCycleDates()
    logInAdmin(self)
  
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
    assertDraftAppMatch(self, draft, app, False)
   
@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class DraftTests(TestCase):
  
  fixtures = ['test_grants.json',]
  
  def setUp(self):
    setCycleDates()
    logInTesty(self)
  
  def test_autosave1(self):
    """ scenario: steal contents of draft 2, turn it into a dict. submit that as request.POST for cycle 5
        verify: draft contents match  """
    complete_draft = DraftGrantApplication.objects.get(pk=2)
    new_draft = DraftGrantApplication(organization = Organization.objects.get(pk=2), grant_cycle = GrantCycle.objects.get(pk=5))
    new_draft.save()
    dict = json.loads(complete_draft.contents)
    
    response = self.client.post('/apply/5/autosave/', dict)
    self.assertEqual(200, response.status_code)
    new_draft = DraftGrantApplication.objects.get(organization_id =2, grant_cycle_id=5)
    self.assertEqual(json.loads(complete_draft.contents), json.loads(new_draft.contents))
  
  """ TO DO
  @override_settings(DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage', MEDIA_ROOT = 'media/', FILE_UPLOAD_HANDLERS = ('django.core.files.uploadhandler.MemoryFileUploadHandler',))
  def test_add_file(self):
    
    budget = open('sjfnw/grants/fixtures/test_grants_guide.txt')
    form_data = {'budget': budget}
    
    response = self.client.post('/apply/2/add-file/', form_data)
    budget.close()

    self.assertEqual(200, response.status_code)
    
  def discard(self):
    pass
    
  """

  """ TO DO 
@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class HomePageTests(TestCase):
  
  # Viewing data on the home page
      #  submitted apps sorting
      #  display of submitted, drafts, past-due drafts
      #  display/sorting of cycles
  def load_home_page(self):
    pass
    
"""