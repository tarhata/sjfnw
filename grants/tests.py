from django.test import TestCase
from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.utils import timezone
from django.utils.html import strip_tags
from grants.models import GrantApplication, DraftGrantApplication, Organization, GrantCycle
import sys, datetime, re

def setPaths():
  #add libs to the path that dev_appserver normally takes care of
  sys.path.append('C:\Program Files (x86)\Google\google_appengine\lib\yaml\lib')
  sys.path.append('C:\Program Files (x86)\Google\google_appengine\lib\webob_1_1_1')

def setCycleDates():
  #open, open, closed, upcoming, open
  now = timezone.now()
  ten_days = datetime.timedelta(days=10)
  twenty_days = datetime.timedelta(days=20)
  
  cycle = GrantCycle.objects.get(pk=1)
  cycle.open = now - ten_days
  cycle.close = now + ten_days
  cycle.save()
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

def logInTesty(self): #'OfficeMax Foundation' pk 2. Submitted 1, draft 1
  self.user = User.objects.create_user('testacct@gmail.com', 'testacct@gmail.com', 'testy')
  self.client.login(username = 'testacct@gmail.com', password = 'testy')

def logInNewbie(self): #'Fresh New Org' pk 1
  user = User.objects.create_user('newacct@gmail.com', 'newacct@gmail.com', 'noob')
  self.client.login(username = 'newacct@gmail.com', password = 'noob')

TEST_MIDDLEWARE = ('django.middleware.common.CommonMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware', 'fund.middleware.MembershipMiddleware',)

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class ApplyTests(TestCase):
  
  fixtures = ['grants/fixtures/test_grants.json',] 
  
  def setUp(self):
    setPaths()
    logInNewbie(self)
    setCycleDates()
    self.org = Organization.objects.get(pk = 1)
  
  @override_settings(DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage')
  @override_settings(MEDIA_ROOT = 'media/')
  @override_settings(FILE_UPLOAD_HANDLERS = ('django.core.files.uploadhandler.MemoryFileUploadHandler',))
  def test_post_valid_app(self):
    """ Updates org profile
        Creates a new application object
        Does not leave a draft object """
    
    self.assertEqual(0, GrantApplication.objects.filter(organization_id = 1, grant_cycle_id = 1).count())
    self.assertEqual(0, DraftGrantApplication.objects.filter(organization_id = 1, grant_cycle_id = 1).count())
    self.assertFalse(self.org.mission)
    
    #fake form submit using same txt for all 3 files
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
    
    #POST
    response = self.client.post('/apply/1/', form_data)
    budget.close()
    funding_sources.close()
    demographics.close()
    
    self.org = Organization.objects.get(pk = 1)
    self.assertEqual(self.org.mission, u'A kmission statement of some importance!')
    self.assertEqual(1, GrantApplication.objects.filter(organization_id = 1, grant_cycle_id = 1).count())
    self.assertEqual(0, DraftGrantApplication.objects.filter(organization_id = 1, grant_cycle_id = 1).count())
    #self.assertTemplateUsed(response, 'grants/submitted.html')
    self.assertEqual(response.status_code, 302)

class PageLoadTests(TestCase):
    
  def load_first_app(self):
    pass
    #expect empty form
  
  def load_second_app(self):
    pass
    #expect profile fields
  
  def load_home_page(self):
    pass
    """ submitted apps sorting
        display of submitted, drafts, past-due drafts
        display/sorting of cycles"""

class BlockedLoadTests(TestCase):
  """apply to non-existent cycle
    apply to closed cycle
    apply to upcoming cycle
    apply to one you've applied to"""
        
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

"""
class GrantApplicationTests(TestCase)     
  
  #just copied from stackoverflow, needs work
  def test_a_file(self):
    import tempfile
    import os
    filename = tempfile.mkstemp()[1]
    f = open(filename, 'w')
    f.write('These are the file contents')
    f.close()
    f = open(filename, 'r')
    post_data = {'file': f}
    response = self.client.post('/apply/4/', post_data)
    f.close()
    os.remove(filename)
    self.assertTemplateUsed(response, 'tests/solution_detail.html')
    self.assertContains(response, os.path.basename(filename))
  """