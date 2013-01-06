from django.test import TestCase
from django.test.client import Client
from fund import models
from django.contrib.auth.models import User
import sys
 
class StepCompleteTest(TestCase):
    fixtures = ['fund/fixtures/test_fund.json',]
    
    def setUp(self):
      #add libs to the path that dev_appserver normally takes care of
      sys.path.append('C:\Program Files (x86)\Google\google_appengine\lib\yaml\lib')
      sys.path.append('C:\Program Files (x86)\Google\google_appengine\lib\webob_1_1_1')
      
      self.client = Client()
      user = User.objects.create_user('testacct@gmail.com', 'testacct@gmail.com', 'testy')
      self.client.login(username = 'testacct@gmail.com', password = 'testy')
      
    # valid data
    def test_valid_asked(self): #asked only
      form_data = {'asked': 'on',
          'response': 2,
          'pledged_amount': '',
          'last_name': '',
          'notes': '',
          'next_step': '',
          'next_step_date': ''}
      
      response = self.client.post('/fund/1/1/done', form_data)
      #expect an HttpResponse("success")
      self.assertEqual(response.content, "success")
      
    # invalid data
    def test_invalid_asked(self): #pledged w/o amt
      form_data = {'asked': 'on',
          'response': 1,
          'pledged_amount': '',
          'last_name': '',
          'notes': '',
          'next_step': '',
          'next_step_date': ''}
      
      response = self.client.post('/fund/1/1/done', form_data)
      form = response.context['form']
      #expect error message on pledged_amount
      assert form.errors['pledged_amount'] is not None
      
    
    
"""
test ideas:
  registration
  step complete
  fresh page w/o contacts
  pre & post estimate
  notifications
  forms in general
  attempt regis w/repeat & non
"""