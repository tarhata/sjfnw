from django.test import TestCase
from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.utils import timezone
from django.utils.html import strip_tags
from grants.models import GrantApplication, DraftGrantApplication, Organization, GrantCycle
import sys, datetime, re

def setPaths():
  """ add libs to the path that dev_appserver normally takes care of """
  sys.path.append('C:\Program Files (x86)\Google\google_appengine\lib\yaml\lib')
  sys.path.append('C:\Program Files (x86)\Google\google_appengine\lib\webob_0_9')

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

TEST_MIDDLEWARE = ('django.middleware.common.CommonMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware', 'fund.middleware.MembershipMiddleware',)

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class ApplyTests(TestCase):
  
  """ Submitting an application """
  
  """ TODO
        apply with deadline extension
        validate fiscal
        validate collab 
        possibly using draft-saved files """

  fixtures = ['grants/fixtures/test_grants.json',] 
  
  def setUp(self):
    setPaths()
    setCycleDates()
  
  @override_settings(DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage', MEDIA_ROOT = 'media/', FILE_UPLOAD_HANDLERS = ('django.core.files.uploadhandler.MemoryFileUploadHandler',))
  def test_post_valid_app(self):
    """ (Does not test blobstore file handling)
        Updates org profile
        Creates a new application object
        No draft object """
    
    logInNewbie(self)
    
    org = Organization.objects.get(pk = 1)
    self.assertEqual(0, GrantApplication.objects.filter(organization_id = 1, grant_cycle_id = 1).count())
    self.assertEqual(0, DraftGrantApplication.objects.filter(organization_id = 1, grant_cycle_id = 1).count())
    self.assertFalse(org.mission)
    
    form_data = {u'website': [u'asdfsdaf'],
            u'mission': [u'A kmission statement of some importance!'],
            u'founded': [u'351'],
            u'fiscal_telephone': [u''],
            u'email_address': [u'as@gmail.com'],
            u'city': [u'sdaf'],
            u'amount_requested': [u'100000'],
            u'zip': [u'654'],
            u'start_year': [u'sdfsadfdsf'],
            u'project_budget': [u''],
            u'support_type': [u'General support'],
            u'state': [u'OR'],
            u'fiscal_org': [u''],
            u'status': [u'501c3'],u'narrative1': [u'adasrdsadssdfsdfsdfsdfdfsdfsdfdfsdfsdf\r\r\ndfsdfsdfdfsdfsdfdfsdfsdfdfsdfsdfsdfsdfdfsdfsdfdfsdfsdfdfsdfsdfdfdfsdfdfsdfsdfdfsdfsdfdfdfsdfsdfdfsdfsdfdfsdfsdf'],
            u'narrative2': [u'sdfsdfsdfitizes groups that understand and address the underlying, or root causes of the issues, and that bring people together to build collective power.\r\r\nWhat problems, needs or issues does your work address?\r\r\nWhat are the root causes of these'],
            u'narrative3': [u'sdfasfsdfsdfdsfdsfsdffsdfitizes groups that understand and address the underlying, or root causes of the issues, and that bring people together to build collective power.\r\r\nWhat problems, needs or issues does your work address?\r\r\nWhat are theroot causes of thesefdsfsdfsdfsdfsdfsdfsdfsdfds'],
            u'narrative4': [u'itizes groups that understand and address the underlying, or root causes of the issues, and that bring people together to build collective power.\r\r\nWhat problems, needs or issues does your work address?\r\r\nWhat are the root causes of theseitizesgroups that understand and address the underlying, or root causes of the issues, and that bring people together to build collective power.\r\r\nWhat problems, needs or issues does your work address?\r\r\nWhat are the root causes of these'],
            u'narrative5': [u'itizes groups that understand and address the underlying, orroot causes of the issues, and that bring people together to build collective power.\r\r\nWhat problems, needs or issues does your work address?\r\r\nWhat are the root causes of theseitizes groups that understand and address the underlying, or root causes of the issues, and that bring people together to build collective power.\r\r\nWhat problems, needs or issues does your work address?\r\r\nWhat are the root causes of these'],
            u'narrative6': [u'itizes groups that klady adskhaskjdfhasdkjgfsa faksjdhfsakdfh ogether to build collective power.\r\r\nWhat problems, needs or issues does your work address?\r\r\nWhat are the root causes of these'],
            u'fax_number': [u'321'],
            u'budget_last': [u'256161'],
            u'address': [u'asdfsdf'],
            u'fiscal_email': [u''],
            u'grant_period': [u'sdfgsdfdsaf'],
            u'previous_grants': [u'dsfsadfsfdsa dsg gdfg sadfdsg fd g'],
            u'grant_request': [u'A grant rewuireasjdflsdfasdg'],
            u'fiscal_person': [u''],
            u'project_title': [u''],
            u'budget_current': [u'62561'],
            u'fiscal_address': [u''],
            u'telephone_number': [u'325'],
            u'contact_person': [u'asdfsadfasdfasdf'],
            u'contact_person_title': [u'Dr Mr'],
            u'ein': [u'654'],
            u"collab_ref1_name": "Audrey", 
            u"collab_ref1_phone": [u"206568756"], 
            u"collab_ref1_org": [u"Organzzzz"], 
            u"collab_ref2_name": [u"Hep"], 
            u"collab_ref2_phone": [u""], 
            u"collab_ref2_org": [u"RFLAEKJRKH"], 
            u"collab_ref2_email": [u"asdasdsad@gface.com"], 
            u"collab_ref1_email": [u"adsasd@gjadslf.com"],
            u'screening_status': [u'10'],
    }
    form_data['grant_cycle'] = u'1'
    form_data['organization'] = u'1',
    budget =  open('grants/fixtures/test_grants_guide.txt')
    form_data['budget'] = budget
    funding_sources =  open('static/grant_app/funding.doc')
    form_data['funding_sources'] = funding_sources
    demographics = open('static/css/admin.css')
    form_data['demographics'] = demographics

    response = self.client.post('/apply/1/', form_data, follow=True)
    budget.close()
    funding_sources.close()
    demographics.close()
    
    org = Organization.objects.get(pk = 1)
    self.assertEqual(org.mission, u'A kmission statement of some importance!')
    self.assertEqual(1, GrantApplication.objects.filter(organization_id = 1, grant_cycle_id = 1).count())
    self.assertEqual(0, DraftGrantApplication.objects.filter(organization_id = 1, grant_cycle_id = 1).count())
    self.assertTemplateUsed(response, 'grants/submitted.html')

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class ApplyBlockedTests(TestCase):

  """ Attempting to access an invalid application/cycle """
  
  fixtures = ['grants/fixtures/test_grants.json',] 
  
  def setUp(self):
    setPaths()
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
  
  fixtures = ['grants/fixtures/test_grants.json',] 
  
  def setUp(self):
    setPaths()
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
    self.assertEqual('', response.context['saved']) #make sure we didn't load a draft

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
    self.assertEqual('', response.context['saved']) #make sure we didn't load a draft

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class HomePageTests(TestCase):
  
  """ Viewing data on the home page
        submitted apps sorting
        display of submitted, drafts, past-due drafts
        display/sorting of cycles"""
  def load_home_page(self):
    pass

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class DraftTests(TestCase):
   #can't test autosave here..?
  def discard(self):
    pass
    #discard a draft
    
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