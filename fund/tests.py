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
  
  fixtures = ['fund/fixtures/test_fund.json',]
  
  def setUp(self):
    setPaths()      
    logInTesty(self)
    
  def test_valid_asked(self):
    
    """ asked + undecided = valid form input
        step.completed set
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
    
    self.assertEqual(pre_count + 1, models.Step.objects.count())
    self.assertEqual(1, models.Step.objects.filter(description = 'A BRAND NEW STEP').count())
  
  def test_valid_response(self):
    """ TO DO
    contact that was already asked
    add a response 
    make sure step.asked stays false """
    pass
    
  def test_valid_followup1(self):
    
    """ last name + phone = valid
        step.pledged updated
        donor fields updated """
    
    form_data = {'asked': 'on',
      'response': 1,
      'pledged_amount': 50,
      'last_name': 'Sozzity',
      'phone': '',
      'email': 'blah@gmail.com',
      'notes': '',
      'next_step': 'A BRAND NEW STEP',
      'next_step_date': '2013-01-25'}
    
    response = self.client.post('/fund/1/1/done', form_data)
    self.assertEqual(response.content, "success")
    
    donor1 = models.Donor.objects.get(pk=1)
    self.assertEqual(donor1.lastname, 'Sozzity')
    self.assertEqual(donor1.email, 'blah@gmail.com')
    step1 = models.Step.objects.get(pk=1)
    self.assertEqual(step1.pledged, 50)
    
  def test_valid_followup2(self):
  
    """ last name + email = valid
        donor fields updated """
    
    form_data = {'asked': 'on',
      'response': 1,
      'pledged_amount': 50,
      'last_name': 'Sozzity',
      'phone': '206-555-5898',
      'email': '',
      'notes': '',
      'next_step': 'A BRAND NEW STEP',
      'next_step_date': '2013-01-25'}
  
    response = self.client.post('/fund/1/1/done', form_data)
    self.assertEqual(response.content, "success")
    
    donor1 = models.Donor.objects.get(pk=1)
    self.assertEqual(donor1.lastname, 'Sozzity')
    self.assertEqual(donor1.phone, '206-555-5898')
  
  def test_valid_hiddendata1(self):
    
    """ pledge amt + follow up + undecided
      amt & follow up info should not be saved """
      
    form_data = {'asked': 'on',
      'response': 2,
      'pledged_amount': 50,
      'last_name': 'Sozzity',
      'phone': '206-555-5898',
      'email': '',
      'notes': '',
      'next_step': '',
      'next_step_date': ''}
  
    response = self.client.post('/fund/1/1/done', form_data)
    self.assertEqual(response.content, "success")
    
    donor1 = models.Donor.objects.get(pk=1)
    self.assertNotEqual(donor1.lastname, 'Sozzity')
    self.assertNotEqual(donor1.phone, '206-555-5898')
    self.assertIsNone(donor1.pledged)
    step1 = models.Step.objects.get(pk=1)
    self.assertIsNone(step1.pledged)

  def test_valid_hiddendata2(self):
    
    """ declined + pledge amt + follow up
      amt & follow up info should not be saved
      step.pledged & donor.pledged = 0 """
      
    form_data = {'asked': 'on',
      'response': 3,
      'pledged_amount': 50,
      'last_name': 'Sozzity',
      'phone': '206-555-5898',
      'email': '',
      'notes': '',
      'next_step': '',
      'next_step_date': ''}
  
    response = self.client.post('/fund/1/1/done', form_data)
    self.assertEqual(response.content, "success")
    
    donor1 = models.Donor.objects.get(pk=1)
    self.assertNotEqual(donor1.lastname, 'Sozzity')
    self.assertNotEqual(donor1.phone, '206-555-5898')
    self.assertEqual(donor1.pledged, 0)
    step1 = models.Step.objects.get(pk=1)
    self.assertEqual(step1.pledged, 0)
  
  def test_valid_hiddendata3(self):
    
    """ pledge amt + follow up + undecided
      allow without followup
      don't save pledge on donor or step """
      
    form_data = {'asked': 'on',
      'response': 2,
      'pledged_amount': 50,
      'last_name': '',
      'phone': '',
      'email': '',
      'notes': '',
      'next_step': '',
      'next_step_date': ''}
  
    response = self.client.post('/fund/1/1/done', form_data)
    self.assertEqual(response.content, "success")
    
    donor1 = models.Donor.objects.get(pk=1)
    self.assertIsNone(donor1.pledged)
    step1 = models.Step.objects.get(pk=1)
    self.assertIsNone(step1.pledged)
    
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
    
    self.assertTemplateUsed(response, 'fund/done_step.html')
    self.assertFormError(response, 'form', 'pledged_amount', "Enter an amount.")
    self.assertFormError(response, 'form', 'last_name', "Enter a last name.")
    self.assertFormError(response, 'form', 'phone', "Enter a phone number or email.")
    
    step1 = models.Step.objects.get(pk=1)
    donor1 = models.Donor.objects.get(pk=1)
    
    self.assertIsNone(step1.completed)
    self.assertFalse(step1.asked)
    self.assertFalse(donor1.asked)

  def test_invalid_next(self):
    
    """ missing date
        missing desc """
    
    form_data = {'asked': '',
        'response': 2,
        'pledged_amount': '',
        'last_name': '',
        'notes': '',
        'next_step': 'A step description!',
        'next_step_date': ''}
    
    response = self.client.post('/fund/1/1/done', form_data)
    
    self.assertTemplateUsed(response, 'fund/done_step.html')
    self.assertFormError(response, 'form', 'next_step_date', "Enter a date.")
    
    step1 = models.Step.objects.get(pk=1)
    self.assertIsNone(step1.completed)
    
    form_data = {'asked': '',
        'response': 2,
        'pledged_amount': '',
        'last_name': '',
        'notes': '',
        'next_step': '',
        'next_step_date': '2013-01-25'}
    
    response = self.client.post('/fund/1/1/done', form_data)
    self.assertTemplateUsed(response, 'fund/done_step.html')
    self.assertFormError(response, 'form', 'next_step', "Enter a description.")
    
    step1 = models.Step.objects.get(pk=1)
    self.assertIsNone(step1.completed)
       
class MainPageContent(TestCase):      
  
  fixtures = ['fund/fixtures/test_fund.json',]
  
  def setUp(self):
    setPaths()
    logInNewbie(self)    
    
  def test_new(self):
    
    """ no contacts 
        logged into pre gp, sees mass add pre
        logged into post gp, sees reg mass add """
    
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
    
  def test_no_estimates(self):
   
    """ 2 contacts w/o est
        logs into post training, gets estimates form
        logs into pre, does not """
    
    membership = models.Membership.objects.get(pk = 2)
    
    contact = models.Donor(firstname = 'Anna', membership = membership)
    contact.save()
    contact = models.Donor(firstname = 'Banana', membership = membership)
    contact.save()
    
    response = self.client.get('/fund/')
    self.assertTemplateUsed('fund/add_estimates.html')
    
    member = membership.member
    member.current = 3 # the pre-training one
    member.save()
    
    membership = models.Membership.objects.get(pk = 3)
    
    contact = models.Donor(firstname = 'Anna', membership = membership)
    contact.save()
    contact = models.Donor(firstname = 'Banana', membership = membership)
    contact.save()
    
    response = self.client.get('/fund/')
    self.assertTemplateNotUsed('fund/add_estimates.html')

  def test_estimates(self):
     
    """ 2 contacts w/est
        logs into post training, gets reg list """
    
    membership = models.Membership.objects.get(pk = 2)
    
    contact = models.Donor(firstname = 'Anna', membership = membership, amount = 0, likelihood = 0)
    contact.save()
    contact = models.Donor(firstname = 'Banana', membership = membership, amount = 567, likelihood = 34)
    contact.save()
    
    response = self.client.get('/fund/')
    self.assertTemplateNotUsed('fund/add_estimates.html')
  
  def test_gift_notification(self):
    
    """ add a gift to donor
        test that notif shows up on next load
        test that notif is gone on next load """
  
"""
 TEST IDEAS
 
  registration
  gift notification & email
  forms in general
  update story
    
"""