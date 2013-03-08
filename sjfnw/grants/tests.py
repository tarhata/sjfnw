from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone
from django.utils.html import strip_tags
from models import GrantApplication, DraftGrantApplication, Organization, GrantCycle
import sys, datetime, re

def setCycleDates(just_open = False):
  """ Updates grant cycle dates to make sure they have the expected statuses:
      open, open, closed, upcoming, open """
      
  now = timezone.now()
  ten_days = datetime.timedelta(days=10)
  
  cycle = GrantCycle.objects.get(pk=1)
  cycle.open = now - ten_days
  cycle.close = now + ten_days
  cycle.save()
  if not just_open:
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

TEST_MIDDLEWARE = ('django.middleware.common.CommonMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware', 'sjfnw.fund.middleware.MembershipMiddleware',)

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class ApplyTests(TestCase):
  
  """ Submitting an application """
  
  """ TODO
        apply with deadline extension
        validate fiscal
        validate collab 
        possibly using draft-saved files """

  fixtures = ['test_grants.json',] 
  
  def setUp(self):
    setCycleDates()
  
  @override_settings(DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage', MEDIA_ROOT = 'media/', FILE_UPLOAD_HANDLERS = ('django.core.files.uploadhandler.MemoryFileUploadHandler',))
  def test_add_file(self):
    """
    budget =  open('sjfnw/grants/fixtures/test_grants_guide.txt')
    form_data['budget'] = budget
    funding_sources =  open('sjfnw/static/grant_app/funding_sources.doc')
    form_data['funding_sources'] = funding_sources
    demographics = open('sjfnw/static/css/admin.css')
    form_data['demographics'] = demographics
    
    response = 
    
    budget.close()
    funding_sources.close()
    demographics.close()
    """
    pass
  
  @override_settings(DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage', MEDIA_ROOT = 'media/', FILE_UPLOAD_HANDLERS = ('django.core.files.uploadhandler.MemoryFileUploadHandler',))
  def test_post_valid_app(self):
    """ scenario: start with a complete draft, post to apply
                  general, no fiscal, all-in-one budget

        verify: response is success page
                grantapplication created
                draft deleted
                email sent
                org profile updated """
    
    logInTesty(self)
    
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

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class ApplyBlockedTests(TestCase):
  """ Attempting to access an invalid application/cycle """
  
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
class StartApplicationTests(TestCase):
  """Starting (loading) an application for an open cycle."""
  
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

class RolloverTests(TestCase):
  
  fixtures = []
  def setUp(self):
    logInTesty(self)

""" TO DO """


@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class ApplyTests(TestCase): #OUT OF DATE 3/4
  
  """ Submitting an application """
  
  """ TODO
        apply with deadline extension
        validate fiscal
        validate collab 
        possibly using draft-saved files """

  fixtures = ['test_grants.json',] 
  
  def setUp(self):
    setCycleDates()
  
  @override_settings(DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage', MEDIA_ROOT = 'media/', FILE_UPLOAD_HANDLERS = ('django.core.files.uploadhandler.MemoryFileUploadHandler',))
  def test_post_valid_app(self): #OUT OF DATE 3/4
    pass
    """(Does not test blobstore file handling)
        Updates org profile
        Creates a new application object
        No draft object 
    
    logInNewbie(self)
    
    org = Organization.objects.get(pk = 1)
    self.assertEqual(0, GrantApplication.objects.filter(organization_id = 1, grant_cycle_id = 1).count())
    self.assertEqual(0, DraftGrantApplication.objects.filter(organization_id = 1, grant_cycle_id = 1).count())
    self.assertFalse(org.mission)
    

    budget =  open('sjfnw/grants/fixtures/test_grants_guide.txt')
    form_data['budget'] = budget
    funding_sources =  open('sjfnw/static/grant_app/funding_sources.doc')
    form_data['funding_sources'] = funding_sources
    demographics = open('sjfnw/static/css/admin.css')
    form_data['demographics'] = demographics

    response = self.client.post('/apply/1/', form_data, follow=True)
    budget.close()
    funding_sources.close()
    demographics.close()
    
    #form = response.context['form']
    #print(form.errors)
    org = Organization.objects.get(pk = 1)
    self.assertTemplateUsed(response, 'grants/submitted.html')
    self.assertEqual(org.mission, u'A kmission statement of some importance!')
    self.assertEqual(1, GrantApplication.objects.filter(organization_id = 1, grant_cycle_id = 1).count())
    self.assertEqual(0, DraftGrantApplication.objects.filter(organization_id = 1, grant_cycle_id = 1).count())
    """

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class DraftTests(TestCase):

  def discard(self):
    pass

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class HomePageTests(TestCase):
  
  """ Viewing data on the home page
        submitted apps sorting
        display of submitted, drafts, past-due drafts
        display/sorting of cycles"""
  def load_home_page(self):
    pass

""" TESTS TO DO
    
  try to access pages without being registered
  file upload/serving?
 
  FIXTURE NEEDS
    orgs:
      brand new
      has saved profile
      has applied to 1+ open apps
      has saved draft that's still open
      has saved draft that's past-due
 """