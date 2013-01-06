from django.test import TestCase
from django.test.client import Client
from fund import models
from django.contrib.auth.models import User
import logging
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
      

    def test_valid_asked(self):
      form_data = {'asked': 'on',
          'response': 2,
          'pledged_amount': '',
          'last_name': '',
          'notes': '',
          'next_step': '',
          'next_step_date': ''}
      
      response = self.client.post('/fund/1/1/', form_data)
      print(response.templates)
      self.assertEqual(response.status_code, 200)
      
    
    
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