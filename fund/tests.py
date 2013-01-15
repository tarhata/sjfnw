from django.test import TestCase
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

def logInNewbie(self):
  user = User.objects.create_user('newacct@gmail.com', 'newacct@gmail.com', 'noob')
  self.client.login(username = 'newacct@gmail.com', password = 'noob')

class StepCompleteTest(TestCase):
  
  """ 
   TO DO:
    invalid next step
    valid pledge amount follow up
    weird conflicting data as if showed/hidden
    correct spans shown/hidden (on GET and POST)
    
    news creation can't be tested since deferred breaks tests. unless we stop using deferred
  """
  
  fixtures = ['fund/fixtures/test_fund.json',]
  
  def setUp(self):
    setPaths()      
    logInTesty(self)
    
  def test_valid_asked(self):
    
    """ asked + undecided = valid form input
        step.asked false -> true
        donor.asked false -> true """
    
    form_data = {'asked': 'on',
        'response': 2,
        'pledged_amount': '',
        'last_name': '',
        'notes': '',
        'next_step': '',
        'next_step_date': ''}
    
    step1 = models.Step.objects.get(pk=1)
    donor1 = models.Donor.objects.get(pk=1)
    
    self.assertIsNone(step1.completed)
    self.assertFalse(step1.asked)
    self.assertFalse(donor1.asked)
    
    response = self.client.post('/fund/1/1/done', form_data)
    self.assertEqual(response.content, "success")
    
    step1 = models.Step.objects.get(pk=1) 
    donor1 = models.Donor.objects.get(pk=1)
    
    self.assertIsNotNone(step1.completed)
    self.assertTrue(step1.asked)
    self.assertTrue(donor1.asked)
    
  def test_valid_next(self):
    
    """ no input on top = valid
        step completed
        desc + date creates new step """
    
    form_data = {'asked': '',
        'response': 2,
        'pledged_amount': '',
        'last_name': '',
        'notes': '',
        'next_step': 'A BRAND NEW STEP',
        'next_step_date': '2013-01-25'}

    pre_count = models.Step.objects.count()
    
    response = self.client.post('/fund/1/1/done', form_data)
    self.assertEqual(response.content, "success")
    
    #step completed
    
    self.assertEqual(pre_count + 1, models.Step.objects.count())
    self.assertEqual(1, models.Step.objects.filter(description = 'A BRAND NEW STEP').count())
    
  def test_invalid_asked(self):
    
    """ pledge w/no amount, last name, phone or email gives errors
        step.completed stays null
        step.asked stays False
        donor.asked stays False """
    
    form_data = {'asked': 'on',
        'response': 1,
        'pledged_amount': '',
        'last_name': '',
        'notes': '',
        'next_step': '',
        'next_step_date': ''}
    
    step1 = models.Step.objects.get(pk=1)
    donor1 = models.Donor.objects.get(pk=1)
    
    self.assertIsNone(step1.completed)
    self.assertFalse(step1.asked)
    self.assertFalse(donor1.asked)
    
    response = self.client.post('/fund/1/1/done', form_data)
    
    self.assertFormError(response, 'form', 'pledged_amount', "Please enter an amount.")
    self.assertFormError(response, 'form', 'last_name', "Please enter a last name.")
    self.assertFormError(response, 'form', 'phone', "Please enter a phone number or email address.")
    
    step1 = models.Step.objects.get(pk=1)
    donor1 = models.Donor.objects.get(pk=1)
    
    self.assertIsNone(step1.completed)
    self.assertFalse(step1.asked)
    self.assertFalse(donor1.asked)

class MainPageContent(TestCase):      
  
  """ TO DO
    mass add form (2 variations)
    contacts list
    add estimates form
  """
  
  fixtures = ['fund/fixtures/test_fund.json',]
  
  def setUp(self):
    setPaths()      
    
  def test_new(self):
    
    """ brand new user 
          logged into pre gp, sees mass add pre
          logged into post gp, sees reg mass add """
    
    logInNewbie(self)
    
    membership = models.Membership.objects.get(pk = 2)
    
    response = self.client.get('/fund/')
    self.assertTemplateUsed(response, 'fund/add_mult.html')
    self.assertEqual(response.context['membership'], membership)
    
    member = membership.member
    member.current = 3 # the pre-training one
    member.save()
    
    response = self.client.get('/fund/')
    
    membership = models.Membership.objects.get(pk = 3)
    self.assertTemplateUsed(response, 'fund/add_mult_pre.html')
    self.assertEqual(response.context['membership'], membership)
    
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
  different starting data? diff user? etc?
  
  add checks for data, not just response output
  registration
  fresh page w/o contacts
  pre & post estimate
  notifications
  forms in general
  attempt regis w/repeat & non
"""

""" FIXTURES REF """
