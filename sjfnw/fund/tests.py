from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from django.utils import timezone

from sjfnw.constants import TEST_MIDDLEWARE
from sjfnw.fund import models
from sjfnw.tests import BaseTestCase

from datetime import timedelta
import unittest, logging
logger = logging.getLogger('sjfnw')


def set_project_dates():
  """ Sets giving project training and deadline dates """
  today = timezone.now()
  gp = models.GivingProject.objects.get(pk=1) #post
  gp.fundraising_training = today - timedelta(days=10)
  gp.fundraising_deadline = today + timedelta(days=80)
  gp.save()
  gp = models.GivingProject.objects.get(pk=2) #pre
  gp.fundraising_training = today + timedelta(days=10)
  gp.fundraising_deadline = today + timedelta(days=30)
  gp.save()

class BaseFundTestCase(BaseTestCase):
  """ Base test case for fundraising tests

  Defines:
    Fixtures (all live dumps)
    setUp
      handles logins based on string passed in
      sets project dates
  """

  fixtures = ['sjfnw/fund/fixtures/live_gp_dump.json',
              'sjfnw/fund/fixtures/live_member_dump.json',
              'sjfnw/fund/fixtures/live_membership_dump.json',
              'sjfnw/fund/fixtures/live_donor_dump.json',
              'sjfnw/fund/fixtures/live_step_dump.json']

  def setUp(self, login):
    super(BaseFundTestCase, self).setUp(login)
    if login == 'testy':
      self.logInTesty()
    elif login == 'newbie':
      self.logInNewbie()
    elif login == 'admin':
      self.logInAdmin()
    set_project_dates()

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class StepComplete(BaseFundTestCase):
  """ Tests various scenarios of test completion

  Uses step 3270, belonging to donor 2900, belonging to membership 1
  (testacct & post-training)
  """

  donor_id = 2900
  step_id = 3270
  url = reverse('sjfnw.fund.views.done_step', kwargs = {
    'donor_id': donor_id, 'step_id': step_id })

  def setUp(self, *args):
    super(StepComplete, self).setUp('testy')

  def test_valid_asked(self):

    """ asked + undecided = valid form input
        step.completed set
        step.asked false -> true
        donor.asked false -> true """

    form_data = {
        'asked': 'on',
        'response': 2,
        'promised_amount': '',
        'last_name': '',
        'notes': '',
        'next_step': '',
        'next_step_date': ''}

    step1 = models.Step.objects.get(pk=self.step_id)
    donor1 = models.Donor.objects.get(pk=self.donor_id)

    self.assertIsNone(step1.completed)
    self.assertFalse(step1.asked)
    self.assertFalse(donor1.asked)

    response = self.client.post(self.url, form_data)
    self.assertEqual(response.content, "success")

    step1 = models.Step.objects.get(pk=self.step_id)
    donor1 = models.Donor.objects.get(pk=self.donor_id)

    self.assertIsNotNone(step1.completed)
    self.assertTrue(step1.asked)
    self.assertTrue(donor1.asked)

  def test_valid_next(self):

    """ no input on top = valid
        step completed
        desc + date creates new step """

    form_data = {'asked': '',
        'response': 2,
        'promised_amount': '',
        'last_name': '',
        'notes': '',
        'next_step': 'A BRAND NEW STEP',
        'next_step_date': '2013-01-25'}

    pre_count = models.Step.objects.count()

    response = self.client.post(self.url, form_data)
    self.assertEqual(response.content, "success")

    self.assertEqual(pre_count + 1, models.Step.objects.count())
    self.assertEqual(1, models.Step.objects.filter(description='A BRAND NEW STEP').count())

  @unittest.skip('Incomplete')
  def test_valid_response(self): #TODO
    """ TO DO
    contact that was already asked
    add a response
    make sure step.asked stays false """
    pass

  def test_valid_followup1(self):

    """ last name + phone = valid
        step.promised updated
        donor fields updated """

    form_data = {'asked': 'on',
      'response': 1,
      'promised_amount': 50,
      'last_name': 'Sozzity',
      'phone': '',
      'email': 'blah@gmail.com',
      'notes': '',
      'next_step': 'A BRAND NEW STEP',
      'next_step_date': '2013-01-25'}

    response = self.client.post(self.url, form_data)
    self.assertEqual(response.content, "success")

    donor1 = models.Donor.objects.get(pk=self.donor_id)
    self.assertEqual(donor1.lastname, 'Sozzity')
    self.assertEqual(donor1.email, 'blah@gmail.com')
    step1 = models.Step.objects.get(pk=self.step_id)
    self.assertEqual(step1.promised, 50)

  def test_valid_followup2(self):

    """ last name + email = valid
        donor fields updated """

    form_data = {'asked': 'on',
      'response': 1,
      'promised_amount': 50,
      'last_name': 'Sozzity',
      'phone': '206-555-5898',
      'email': '',
      'notes': '',
      'next_step': 'A BRAND NEW STEP',
      'next_step_date': '2013-01-25'}

    response = self.client.post(self.url, form_data)
    self.assertEqual(response.content, "success")

    donor1 = models.Donor.objects.get(pk=self.donor_id)
    self.assertEqual(donor1.lastname, 'Sozzity')
    self.assertEqual(donor1.phone, '206-555-5898')

  def test_valid_followup_comma(self):

    """ testing the comma integer field """

    form_data = {'asked': 'on',
      'response': 1,
      'promised_amount': '5,000',
      'last_name': 'Sozzity',
      'phone': '206-555-5898',
      'email': '',
      'notes': '',
      'next_step': 'A BRAND NEW STEP',
      'next_step_date': '2013-01-25'}

    response = self.client.post(self.url, form_data)
    self.assertEqual(response.content, "success")

    donor1 = models.Donor.objects.get(pk=self.donor_id)
    self.assertEqual(donor1.lastname, 'Sozzity')
    self.assertEqual(donor1.phone, '206-555-5898')
    self.assertEqual(donor1.promised, 5000)

  def test_valid_hiddendata1(self):

    """ promise amt + follow up + undecided
      amt & follow up info should not be saved """

    form_data = {'asked': 'on',
      'response': 2,
      'promised_amount': 50,
      'last_name': 'Sozzity',
      'phone': '206-555-5898',
      'email': '',
      'notes': '',
      'next_step': '',
      'next_step_date': ''}

    response = self.client.post(self.url, form_data)
    self.assertEqual(response.content, "success")

    donor1 = models.Donor.objects.get(pk=self.donor_id)
    self.assertNotEqual(donor1.lastname, 'Sozzity')
    self.assertNotEqual(donor1.phone, '206-555-5898')
    self.assertIsNone(donor1.promised)
    step1 = models.Step.objects.get(pk=self.step_id)
    self.assertIsNone(step1.promised)

  def test_valid_hiddendata2(self):

    """ declined + promise amt + follow up
      amt & follow up info should not be saved
      step.promised & donor.promised = 0 """

    form_data = {'asked': 'on',
      'response': 3,
      'promised_amount': 50,
      'last_name': 'Sozzity',
      'phone': '206-555-5898',
      'email': '',
      'notes': '',
      'next_step': '',
      'next_step_date': ''}

    response = self.client.post(self.url, form_data)
    self.assertEqual(response.content, "success")

    donor1 = models.Donor.objects.get(pk=self.donor_id)
    self.assertNotEqual(donor1.lastname, 'Sozzity')
    self.assertNotEqual(donor1.phone, '206-555-5898')
    self.assertEqual(donor1.promised, 0)
    step1 = models.Step.objects.get(pk=self.step_id)
    self.assertEqual(step1.promised, 0)

  def test_valid_hiddendata3(self):

    """ promise amt + follow up + undecided
      allow without followup
      don't save promise on donor or step """

    form_data = {'asked': 'on',
      'response': 2,
      'promised_amount': 50,
      'last_name': '',
      'phone': '',
      'email': '',
      'notes': '',
      'next_step': '',
      'next_step_date': ''}

    response = self.client.post(self.url, form_data)
    self.assertEqual(response.content, "success")

    donor1 = models.Donor.objects.get(pk=self.donor_id)
    self.assertIsNone(donor1.promised)
    step1 = models.Step.objects.get(pk=self.step_id)
    self.assertIsNone(step1.promised)

  def test_invalid_promise(self):
    """ Verify that additional info is required when a promise is entered

    Setup:
      Complete a step with response promised, but no amount, phone or email

    Asserts:
      Form template used (not successful)
      Form errors on promised_amount, last_name, phone
      Step and donor not modified
    """

    form_data = {
        'asked': 'on',
        'response': 1,
        'promised_amount': '',
        'last_name': '',
        'notes': '',
        'next_step': '',
        'next_step_date': ''}

    step1 = models.Step.objects.get(pk=self.step_id)
    donor1 = models.Donor.objects.get(pk=self.donor_id)

    self.assertIsNone(step1.completed)
    self.assertFalse(step1.asked)
    self.assertFalse(donor1.asked)

    response = self.client.post(self.url, form_data)

    self.assertTemplateUsed(response, 'fund/done_step.html')
    self.assertFormError(response, 'form', 'promised_amount', "Enter an amount.")
    self.assertFormError(response, 'form', 'last_name', "Enter a last name.")
    self.assertFormError(response, 'form', 'phone', "Enter a phone number or email.")

    step1 = models.Step.objects.get(pk=self.step_id)
    donor1 = models.Donor.objects.get(pk=self.donor_id)

    self.assertIsNone(step1.completed)
    self.assertFalse(step1.asked)
    self.assertFalse(donor1.asked)

  def test_invalid_next(self):

    """ missing date
        missing desc """

    form_data = {'asked': '',
        'response': 2,
        'promised_amount': '',
        'last_name': '',
        'notes': '',
        'next_step': 'A step description!',
        'next_step_date': ''}

    response = self.client.post(self.url, form_data)

    self.assertTemplateUsed(response, 'fund/done_step.html')
    self.assertFormError(response, 'form', 'next_step_date', "Enter a date in mm/dd/yyyy format.")

    step1 = models.Step.objects.get(pk=self.step_id)
    self.assertIsNone(step1.completed)

    form_data = {'asked': '',
        'response': 2,
        'promised_amount': '',
        'last_name': '',
        'notes': '',
        'next_step': '',
        'next_step_date': '2013-01-25'}

    response = self.client.post(self.url, form_data)
    self.assertTemplateUsed(response, 'fund/done_step.html')
    self.assertFormError(response, 'form', 'next_step', "Enter a description.")

    step1 = models.Step.objects.get(pk=self.step_id)
    self.assertIsNone(step1.completed)

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class Home(BaseFundTestCase):

  url = reverse('sjfnw.fund.views.home')

  def setUp(self):
    super(Home, self).setUp('newbie')

  def test_new(self):
    """ Verify that add mult form is shown to new memberships

    Setup:
      Login to membership in pre-training with 0 contacts
      Login to membership in post-training with 0 contacts

    Asserts:
      Pre: add_mult_pre.html is used
      Post: add_mult.html is used
    """

    membership = models.Membership.objects.get(pk=2) # pre

    response = self.client.get(self.url)
    self.assertTemplateUsed(response, 'fund/add_mult_pre.html')
    self.assertEqual(response.context['membership'], membership)

    member = membership.member
    member.current = 6 # post
    member.save()

    response = self.client.get(self.url)

    membership = models.Membership.objects.get(pk=6)
    self.assertTemplateUsed(response, 'fund/add_mult.html')
    self.assertEqual(response.context['membership'], membership)

  def test_no_estimates(self):

    """ 2 contacts w/o est
        logs into post training, gets estimates form
        logs into pre, does not """

    membership = models.Membership.objects.get(pk=2)

    contact = models.Donor(firstname='Anna', membership=membership)
    contact.save()
    contact = models.Donor(firstname='Banana', membership=membership)
    contact.save()

    response = self.client.get(self.url)
    self.assertTemplateUsed('fund/add_estimates.html')

    member = membership.member
    member.current = 3 # the pre-training one
    member.save()

    membership = models.Membership.objects.get(pk=3)

    contact = models.Donor(firstname='Anna', membership=membership)
    contact.save()
    contact = models.Donor(firstname='Banana', membership=membership)
    contact.save()

    response = self.client.get(self.url)
    self.assertTemplateNotUsed('fund/add_estimates.html')

  def test_estimates(self):

    """ 2 contacts w/est
        logs into post training, gets reg list """

    membership = models.Membership.objects.get(pk=2)

    contact = models.Donor(firstname='Anna', membership=membership, amount=0, likelihood=0)
    contact.save()
    contact = models.Donor(firstname='Banana', membership=membership, amount=567, likelihood=34)
    contact.save()

    response = self.client.get(self.url)
    self.assertTemplateNotUsed('fund/add_estimates.html')

  @unittest.skip('Incomplete')
  def test_gift_notification(self):
    pass

    """ add a gift to donor
        test that notif shows up on next load
        test that notif is gone on next load """

""" TEST IDEAS
      gift notification & email
      update story (deferred) """

