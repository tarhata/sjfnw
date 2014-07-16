from django.test.utils import override_settings

from sjfnw.constants import TEST_MIDDLEWARE
from sjfnw.grants.tests.base import BaseGrantTestCase
from sjfnw.grants import models

import logging
logger = logging.getLogger('sjfnw')



@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class ViewGrantPermissions(BaseGrantTestCase):

  fixtures = ['sjfnw/grants/fixtures/test_grants.json', 'sjfnw/fund/fixtures/test_fund.json']

  def setUp(self):
    pa = models.ProjectApp(application_id = 1, giving_project_id = 2)
    pa.save()

  """ Note: using grant app #1
    Author: testorg@gmail.com (org #2)
    GP: #2, which newacct is a member of, test is not
  """
  def test_author(self):
    self.logInTestorg()

    response = self.client.get('/grants/view/1', follow=True)

    self.assertTemplateUsed(response, 'grants/reading.html')
    self.assertEqual(3, response.context['perm'])

  def test_other_org(self):
    self.logInNeworg()

    response = self.client.get('/grants/view/1', follow=True)

    self.assertTemplateUsed(response, 'grants/reading.html')
    self.assertEqual(0, response.context['perm'])

  def test_staff(self):
    self.logInAdmin()

    response = self.client.get('/grants/view/1', follow=True)

    self.assertTemplateUsed(response, 'grants/reading.html')
    self.assertEqual(2, response.context['perm'])

  def test_valid_member(self):
    self.logInNewbie()

    response = self.client.get('/grants/view/1', follow=True)

    self.assertTemplateUsed(response, 'grants/reading.html')
    self.assertEqual(1, response.context['perm'])

  def test_invalid_member(self):
    self.logInTesty()

    response = self.client.get('/grants/view/1', follow=True)

    self.assertTemplateUsed(response, 'grants/reading.html')
    self.assertEqual(0, response.context['perm'])
