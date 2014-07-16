from django.contrib.auth.models import User
from django.utils import timezone

from sjfnw.grants import models
from sjfnw.tests import BaseTestCase

from datetime import timedelta
import json


""" NOTE: some tests depend on having these files in sjfnw/media
  budget.docx      diversity.doc      funding_sources.docx
  budget1.docx     budget2.txt         budget3.png  """

LIVE_FIXTURES = ['sjfnw/fund/fixtures/live_gp_dump.json', #not using these yet in most
                 'sjfnw/grants/fixtures/orgs.json',
                 'sjfnw/grants/fixtures/grant_cycles.json',
                 'sjfnw/grants/fixtures/apps.json',
                 'sjfnw/grants/fixtures/drafts.json',
                 'sjfnw/grants/fixtures/project_apps.json',
                 'sjfnw/grants/fixtures/gp_grants.json']

def set_cycle_dates():
  """ Updates grant cycle dates to make sure they have the expected statuses:
      open, open, closed, upcoming, open """

  now = timezone.now()
  ten_days = timedelta(days=10)

  cycle = models.GrantCycle.objects.get(pk=1)
  cycle.open = now - ten_days
  cycle.close = now + ten_days
  cycle.save()
  twenty_days = timedelta(days=20)
  cycle = models.GrantCycle.objects.get(pk=2)
  cycle.open = now - ten_days
  cycle.close = now + ten_days
  cycle.save()
  cycle = models.GrantCycle.objects.get(pk=3)
  cycle.open = now - twenty_days
  cycle.close = now - ten_days
  cycle.save()
  cycle = models.GrantCycle.objects.get(pk=4)
  cycle.open = now + ten_days
  cycle.close = now + twenty_days
  cycle.save()
  cycle = models.GrantCycle.objects.get(pk=5)
  cycle.open = now - twenty_days
  cycle.close = now + ten_days
  cycle.save()
  cycle = models.GrantCycle.objects.get(pk=6)
  cycle.open = now - twenty_days
  cycle.close = now + ten_days
  cycle.save()

class BaseGrantTestCase(BaseTestCase):
  """ Base for grants tests. Provides fixture and basic setUp
      as well as several helper functions """

  fixtures = ['sjfnw/grants/fixtures/test_grants.json']

  def logInNeworg(self):
    user = User.objects.create_user('neworg@gmail.com', 'neworg@gmail.com', 'noob')
    self.client.login(username = 'neworg@gmail.com', password = 'noob')

  def logInTestorg(self):
    user = User.objects.create_user('testorg@gmail.com', 'testorg@gmail.com', 'noob')
    self.client.login(username = 'testorg@gmail.com', password = 'noob')

  def setUp(self, login=''):
    super(BaseGrantTestCase, self).setUp(login)
    if login == 'testy':
      self.logInTestorg()
    elif login == 'newbie':
      self.logInNeworg()
    elif login == 'admin':
      self.logInAdmin()
    set_cycle_dates()

  class Meta:
    abstract = True


def assert_app_matches_draft(self, draft, app, exclude_cycle): #only checks fields in draft
  """ Timeline formats:
        submitted: json'd list, in order, no file names
        draft: mixed in with other contents by widget name: timeline_0 - timeline_14 """
  draft_contents = json.loads(draft.contents)
  app_timeline = json.loads(app.timeline)
  for field, value in draft_contents.iteritems():
    if 'timeline' in field:
      i = int(field.split('_')[-1])
      self.assertEqual(value, app_timeline[i])
    else:
      self.assertEqual(value, getattr(app, field))
  for field in models.GrantApplication.file_fields():
    if hasattr(draft, field):
      self.assertEqual(getattr(draft, field), getattr(app, field))
  if exclude_cycle:
    self.assertNotIn('cycle_question', draft_contents)

