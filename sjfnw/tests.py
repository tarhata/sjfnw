from django.contrib.auth.models import User
from django.test import TestCase
from django.test.simple import DjangoTestSuiteRunner

from unittest import TextTestRunner, TextTestResult
from unittest.signals import registerResult
import logging
import sys
import time

""" Shared testing base classes, utilities """


# Sets root & sjfnw loggers level. Comment out for less output.
#logging.getLogger().setLevel(1)
#logging.getLogger('sjfnw').setLevel(1)

class BaseTestCase(TestCase):

  def setUp(self, login):
    pass #self.printName()

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

  def assertMessage(self, response, text):
    """ Asserts that a message (django.contrib.messages) with the given text
        is displayed """
    m = list(response.context['messages'])
    self.assertEqual(1, len(m))
    self.assertEqual(str(m[0]), text)

  class Meta:
    abstract = True


class ColorTestSuiteRunner(DjangoTestSuiteRunner):
  """ Redirects run_suite to ColorTestRunner """

  def run_suite(self, suite, **kwargs):
    return ColorTestRunner(verbosity=2, failfast=self.failfast).run(suite)


class ColorTextResult(TextTestResult):
  """Copied and modified from py2.7

  A test result class that can print formatted text results to a stream.

  Used by TextTestRunner.
  """
  separator1 = '=' * 70
  separator2 = '-' * 70

  def __init__(self, stream, descriptions, verbosity):
    super(ColorTextResult, self).__init__(stream, descriptions, verbosity)

  def getDescription(self, test):
    """ modified to bold test name """
    doc_first_line = test.shortDescription()
    name =  test.id().replace('sjfnw.', '').replace('tests.', '').replace('.test_', '  ')
    if self.descriptions and doc_first_line:
      return '\033[1m' + name + '\033[00m ' + doc_first_line
    else:
      return '\033[1m' + name + '\033[00m '

  def startTest(self, test):
    super(TextTestResult, self).startTest(test)
    if self.showAll:
      self.stream.writeln(self.getDescription(test))

  def addSuccess(self, test):
    super(TextTestResult, self).addSuccess(test)
    if self.showAll:
      self.stream.writeln("    \033[00;32mok\033[00m")
    elif self.dots:
      self.stream.write('.')
      self.stream.flush()

  def addError(self, test, err):
    super(TextTestResult, self).addError(test, err)
    if self.showAll:
      self.stream.writeln("    \033[00;31mERROR\033[00m")
    elif self.dots:
      self.stream.write('E')
      self.stream.flush()

  def addFailure(self, test, err):
    super(TextTestResult, self).addFailure(test, err)
    if self.showAll:
      self.stream.writeln("    \033[00;31mFAIL\033[00m")
    elif self.dots:
      self.stream.write('F')
      self.stream.flush()

  def addSkip(self, test, reason):
    super(TextTestResult, self).addSkip(test, reason)
    if self.showAll:
      self.stream.writeln("    \033[00;33mskipped\033[00m {0!r}".format(reason))
    elif self.dots:
      self.stream.write("s")
      self.stream.flush()

  def addExpectedFailure(self, test, err):
    super(TextTestResult, self).addExpectedFailure(test, err)
    if self.showAll:
      self.stream.writeln("    expected failure")
    elif self.dots:
      self.stream.write("x")
      self.stream.flush()

  def addUnexpectedSuccess(self, test):
    super(TextTestResult, self).addUnexpectedSuccess(test)
    if self.showAll:
      self.stream.writeln("    unexpected success")
    elif self.dots:
      self.stream.write("u")
      self.stream.flush()

  def printErrors(self):
    if self.dots or self.showAll:
      self.stream.writeln()
      self.printErrorList('\033[00;31mERROR\033[00m', self.errors)
      self.printErrorList('\033[00;31mFAIL\033[00m', self.failures)

  def printErrorList(self, flavour, errors):
    for test, err in errors:
      self.stream.writeln(self.separator1)
      self.stream.writeln("%s: \033[1m%s\033[00m" % (flavour, str(test)))
      self.stream.writeln(self.separator2)
      self.stream.writeln("%s" % err)


class ColorTestRunner(TextTestRunner):
  """ Colorizes the summary results at the end
  Uses ColorTextResult instead of TextTestResult """

  def __init__(self, stream=sys.stderr, descriptions=True, verbosity=2,
               failfast=False, buffer=False, resultclass=None):
    super(ColorTestRunner, self).__init__(stream, descriptions, verbosity,
                                          failfast, buffer, resultclass)
    self.resultclass=ColorTextResult

  def run(self, test):
    """ Copied and modified from TextTestRunner

      Run the given test case or test suite."""

    result = self._makeResult()
    registerResult(result)
    result.failfast = self.failfast
    result.buffer = self.buffer
    startTime = time.time()
    startTestRun = getattr(result, 'startTestRun', None)
    if startTestRun is not None:
      startTestRun()
    try:
      test(result)
    finally:
      stopTestRun = getattr(result, 'stopTestRun', None)
      if stopTestRun is not None:
        stopTestRun()
    stopTime = time.time()
    timeTaken = stopTime - startTime
    result.printErrors()
    if hasattr(result, 'separator2'):
      self.stream.writeln(result.separator1)
    run = result.testsRun
    self.stream.writeln(" \033[1mRan %d test%s in %.3fs" %
        (run, run != 1 and "s" or "", timeTaken))
    self.stream.writeln()

    expectedFails = unexpectedSuccesses = skipped = 0
    try:
      results = map(len, (result.expectedFailures,
        result.unexpectedSuccesses,
        result.skipped))
    except AttributeError:
      pass
    else:
      expectedFails, unexpectedSuccesses, skipped = results

    infos = []
    if not result.wasSuccessful():
      self.stream.write(" \033[1;31mFAILED\033[00m")
      failed, errored = map(len, (result.failures, result.errors))
      if failed:
        infos.append("failures = \033[00;31m%d\033[00m" % failed)
      if errored:
        infos.append("errors = \033[00;31m%d\033[00m" % errored)
    else:
      self.stream.write(" \033[1;32mOK\033[00m")
    if skipped:
      infos.append("skipped = \033[00;33m%d\033[00m" % skipped)
    if expectedFails:
      infos.append("expected failures=%d" % expectedFails)
    if unexpectedSuccesses:
      infos.append("unexpected successes=%d" % unexpectedSuccesses)
    if infos:
      self.stream.writeln(" (%s)" % (", ".join(infos),))
    self.stream.write('\n')
    return result


