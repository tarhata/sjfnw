from django.utils import unittest
from django.test.client import Client

from fund import models
from django.contrib.auth.models import User

class StepCompleteTest(unittest.TestCase):
    fixtures = ['test_fund']
    
    def setUp(self):
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