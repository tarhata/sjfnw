from django.core import mail
from django.test.utils import override_settings
from django.utils import timezone

from sjfnw.constants import TEST_MIDDLEWARE
from sjfnw.grants.tests.base import BaseGrantTestCase
from sjfnw.grants import models

from datetime import timedelta
import json, unittest, logging
logger = logging.getLogger('sjfnw')


@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class DraftExtension(BaseGrantTestCase):

  def setUp(self):
    super(DraftExtension, self).setUp(login='admin')

  def test_create_draft(self):
    """ Admin create a draft for Fresh New Org """

    self.assertEqual(0, models.DraftGrantApplication.objects.filter(organization_id=1).count())

    response = self.client.post('/admin/grants/draftgrantapplication/add/',
                                {'organization': '1', 'grant_cycle': '3',
                                 'extended_deadline_0': '2013-04-07',
                                 'extended_deadline_1': '11:19:46'})

    self.assertEqual(response.status_code, 302)
    new = models.DraftGrantApplication.objects.get(organization_id=1) #in effect, asserts 1 draft
    self.assertTrue(new.editable)
    self.assertIn('/admin/grants/draftgrantapplication/', response.__getitem__('location'), )

  @unittest.skip('Incomplete')
  def test_org_drafts_list(self):
    pass

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class Draft(BaseGrantTestCase):

  def setUp(self):
    super(Draft, self).setUp(login='testy')

  def test_autosave1(self):
    """ scenario: steal contents of draft 2, turn it into a dict. submit that as request.POST for cycle 5
        verify: draft contents match  """
    complete_draft = models.DraftGrantApplication.objects.get(pk=2)
    new_draft = models.DraftGrantApplication(organization = models.Organization.objects.get(pk=2), grant_cycle = models.GrantCycle.objects.get(pk=5))
    new_draft.save()
    dic = json.loads(complete_draft.contents)
    #fake a user id like the js would normally do
    dic['user_id'] = 'asdFDHAF34qqhRHFEA'
    self.maxDiff = None

    response = self.client.post('/apply/5/autosave/', dic)
    self.assertEqual(200, response.status_code)
    new_draft = models.DraftGrantApplication.objects.get(organization_id=2, grant_cycle_id=5)
    new_c = json.loads(new_draft.contents)
    del new_c['user_id']
    self.assertEqual(json.loads(complete_draft.contents), new_c)



@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class DraftWarning(BaseGrantTestCase):

  def setUp(self):
    super(DraftWarning, self).setUp(login='admin')

  def test_long_alert(self):
    """ Cycle created 12 days ago with cycle closing in 7.5 days
    Expect email to be sent """

    self.assertEqual(len(mail.outbox), 0)

    now = timezone.now()
    draft = models.DraftGrantApplication.objects.get(pk=2)
    draft.created = now - timedelta(days=12)
    draft.save()
    cycle = models.GrantCycle.objects.get(pk=2)
    cycle.close = now + timedelta(days=7, hours=12)
    cycle.save()

    self.client.get('/mail/drafts/')
    self.assertEqual(len(mail.outbox), 1)

  def test_long_alert_skip(self):
    """ Cycle created now with cycle closing in 7.5 days
    Expect email to not be sent """

    self.assertEqual(len(mail.outbox), 0)

    now = timezone.now()
    draft = models.DraftGrantApplication.objects.get(pk=2)
    draft.created = now
    draft.save()
    cycle = models.GrantCycle.objects.get(pk=2)
    cycle.close = now + timedelta(days=7, hours=12)
    cycle.save()

    self.client.get('/mail/drafts/')
    self.assertEqual(len(mail.outbox), 0)

  def test_short_alert(self):
    """ Cycle created now with cycle closing in 2.5 days """

    self.assertEqual(len(mail.outbox), 0)

    now = timezone.now()
    draft = models.DraftGrantApplication.objects.get(pk=2)
    draft.created = now
    draft.save()
    cycle = models.GrantCycle.objects.get(pk=2)
    cycle.close = now + timedelta(days=2, hours=12)
    cycle.save()

    self.client.get('/mail/drafts/')
    self.assertEqual(len(mail.outbox), 1)

  def test_short_alert_ignore(self):
    """ Cycle created 12 days ago with cycle closing in 2.5 days """
    self.assertEqual(len(mail.outbox), 0)

    now = timezone.now()
    draft = models.DraftGrantApplication.objects.get(pk=2)
    draft.created = now - timedelta(days=12)
    draft.save()
    cycle = models.GrantCycle.objects.get(pk=2)
    cycle.close = now + timedelta(days=2, hours=12)
    cycle.save()

    self.client.get('/mail/drafts/')
    self.assertEqual(len(mail.outbox), 0)

