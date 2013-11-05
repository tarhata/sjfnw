from django.contrib.auth.models import User
from django.test import TestCase

import logging


""" Shared testing base classes, utilities """


# Sets root & sjfnw loggers to DEBUG. Comment out for less output.
logging.getLogger().setLevel(0)
logging.getLogger('sjfnw').setLevel(0)

class BaseTestCase(TestCase):

  def setUp(self, login):
    self.printName()

  def printName(self):
    """ Outputs class name, method name and method desc to console """
    full =  self.id().split('.')
    cls, meth = full[-2], full[-1]
    print('\n\033[1m' + cls + ' ' + meth + '\033[m ' + (self.shortDescription() or ''))

  def logInTesty(self):
    user = User.objects.create_user('testacct@gmail.com', 'testacct@gmail.com', 'testy')
    self.client.login(username = 'testacct@gmail.com', password = 'testy')

  def logInNewbie(self):
    user = User.objects.create_user('newacct@gmail.com', 'newacct@gmail.com', 'noob')
    self.client.login(username = 'newacct@gmail.com', password = 'noob')

  def logInAdmin(self): #just a django superuser
    superuser = User.objects.create_superuser('admin@gmail.com', 'admin@gmail.com', 'admin')
    self.client.login(username = 'admin@gmail.com', password = 'admin')

  def logInNeworg(self):
    user = User.objects.create_user('neworg@gmail.com', 'neworg@gmail.com', 'noob')
    self.client.login(username = 'neworg@gmail.com', password = 'noob')

  def logInTestorg(self):
    user = User.objects.create_user('testorg@gmail.com', 'testorg@gmail.com', 'noob')
    self.client.login(username = 'testorg@gmail.com', password = 'noob')

  def assertMessage(self, response, text):
    m = list(response.context['messages'])
    self.assertEqual(1, len(m))
    self.assertEqual(str(m[0]), text)

  class Meta:
    abstract = True

