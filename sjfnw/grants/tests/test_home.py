from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from django.utils import timezone

from sjfnw.constants import TEST_MIDDLEWARE
from sjfnw.grants.tests.base import BaseGrantTestCase
from sjfnw.grants import models

from datetime import timedelta
import json, logging
logger = logging.getLogger('sjfnw')


@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class OrgHomeAwards(BaseGrantTestCase):
  """ Verify that correct data is showing on the org home page """

  url = reverse('sjfnw.grants.views.org_home')
  template = 'grants/org_home.html'

  def setUp(self):
    super(OrgHomeAwards, self).setUp(login='testy')

  #TODO test mult awards per app

  def test_none(self):
    """ org has no awards. verify no award info is shown """

    response = self.client.get(self.url)

    self.assertTemplateUsed(response, self.template)
    self.assertNotContains(response, 'Agreement mailed')

  def test_early(self):
    """ org has an award, but agreement has not been mailed. verify not shown """
    award = models.GivingProjectGrant(projectapp_id = 1, amount = 9000)
    award.save()

    response = self.client.get(self.url)

    self.assertTemplateUsed(response, self.template)
    self.assertNotContains(response, 'Agreement mailed')

  def test_sent(self):
    """ org has award, agreement mailed. verify shown """
    award = models.GivingProjectGrant(projectapp_id = 1, amount = 9000,
        agreement_mailed = timezone.now()-timedelta(days=1))
    award.save()

    response = self.client.get(self.url)

    self.assertTemplateUsed(response, self.template)
    self.assertContains(response, 'Agreement mailed')

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class OrgRollover(BaseGrantTestCase):
  """ Basic success
  content,   timeline,   files,   not extra cycle q   """

  def setUp(self, *args):
    super(OrgRollover, self).setUp(login='newbie')

  def test_draft_rollover(self):
    """ scenario: take complete draft, make it belong to new org, rollover to cycle 1
        verify:
          success (status code & template)
          new draft created
          new draft contents = old draft contents (ignoring cycle q)
          new draft files = old draft files  """

    draft = models.DraftGrantApplication.objects.get(pk=2)
    draft.organization = models.Organization.objects.get(pk=1)
    draft.save()
    # prior to rollover, make sure target draft does not exist
    self.assertEqual(0, models.DraftGrantApplication.objects.filter(organization_id=1, grant_cycle_id=1).count())

    response = self.client.post('/apply/copy',
        {'cycle':'1', 'draft':'2', 'application':''}, follow=True)

    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, 'grants/org_app.html')
    self.assertEqual(1, models.DraftGrantApplication.objects.filter(organization_id=1, grant_cycle_id=1).count())
    new_draft = models.DraftGrantApplication.objects.get(organization_id = 1, grant_cycle_id = 1)
    old_contents = json.loads(draft.contents) # TODO could this use the compare function defined in base?
    old_cycle_q = old_contents.pop('cycle_question', None)
    new_contents = json.loads(new_draft.contents)
    new_cycle_q = new_contents.pop('cycle_question', '')
    self.assertEqual(old_contents, new_contents)
    self.assertNotEqual(old_cycle_q, new_cycle_q)
    for field in models.GrantApplication.file_fields():
      if hasattr(draft, field):
        self.assertEqual(getattr(draft, field), getattr(new_draft, field))

  def test_app_rollover(self):
    """ scenario: take a submitted app, make it belong to new org, rollover to cycle 1
        verify:
          success (status code & template)
          new draft created
          draft contents = app contents (ignoring cycle q)
          draft files = app files  """

    self.assertEqual(0, models.DraftGrantApplication.objects.filter(organization_id=1, grant_cycle_id=2).count())

    app = models.GrantApplication.objects.get(organization_id=2, grant_cycle_id=1)
    app.organization = models.Organization.objects.get(pk=1)
    app.save()

    response = self.client.post('/apply/copy', {'cycle':'2', 'draft':'', 'application':'1'}, follow=True)

    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, 'grants/org_app.html')
    self.assertEqual(1, models.DraftGrantApplication.objects.filter(organization_id=1, grant_cycle_id=2).count())

    draft = models.DraftGrantApplication.objects.get(organization_id=1, grant_cycle_id=2)
    assert_app_matches_draft(self, draft, app, True)

  def test_rollover_form_display(self):
    """ Verify that rollover form displays correctly for both orgs

    cycle_count = number of open cycles that don't have a draft or app already
    apps_count = number of drafts + number of apps
    (+1 are for the starting option)
    """
    # start out logged into neworg
    response = self.client.get('/apply/copy')
    self.assertTemplateUsed(response, 'grants/org_app_copy.html')
    self.assertEqual(response.context['apps_count'], 0)
    self.assertEqual(response.context['cycle_count'], 4)
    self.assertNotContains(response, 'Select')
    self.client.logout()
    # login to testorg (officemax)
    self.logInTestorg()
    response = self.client.get('/apply/copy')
    self.assertTemplateUsed(response, 'grants/org_app_copy.html')
    self.assertEqual(response.context['apps_count'], 4)
    self.assertEqual(response.context['cycle_count'], 1)
    self.assertContains(response, 'Select')
