from django.test import TestCase
from django.test.client import Client
from fund import models
from django.contrib.auth.models import User
import sys

def setPaths():
  #add libs to the path that dev_appserver normally takes care of
  sys.path.append('C:\Program Files (x86)\Google\google_appengine\lib\yaml\lib')
  sys.path.append('C:\Program Files (x86)\Google\google_appengine\lib\webob_1_1_1')

def logInTesty(self):
  user = User.objects.create_user('testacct@gmail.com', 'testacct@gmail.com', 'testy')
  self.client.login(username = 'testacct@gmail.com', password = 'testy')

class StepCompleteTest(TestCase):
  fixtures = ['fund/fixtures/test_fund.json',]
  
  def setUp(self):
    setPaths()      
    logInTesty(self)
    
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
    
  def test_valid_next(self): #asked only + next step
    form_data = {'asked': 'on',
        'response': 2,
        'pledged_amount': '',
        'last_name': '',
        'notes': '',
        'next_step': 'Talk to',
        'next_step_date': ''}
    
    response = self.client.post('/fund/1/1/done', form_data)
    #expect an HttpResponse("success")
    self.assertEqual(response.content, "success")
    #expect a new step created
    
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

class MainPageContent(TestCase):      
  """Tests the basic display of main page contact - mass add form (2 variations), contacts list, add estimates form """
  
  def setUp(self):
    setPaths()      
    logInTesty(self)
    
  def test_new(self): #brand new user
    pass
    #expect mass add form without estimates
  
  def test_pre_contacts(self): #pre-training, has contacts
    pass
    #expect regular contacts list
  
  def test_post_contacts(self): #post-training, has contacts from pre
    pass
    #expect add estimates form
 
  def test_post_empty(self): #post training, has no contacts
    pass
    #expect add estimates form

"""
test ideas:
  add checks for data, not just response output
  registration
  step complete
  fresh page w/o contacts
  pre & post estimate
  notifications
  forms in general
  attempt regis w/repeat & non
"""

""" FIXTURES REF """
