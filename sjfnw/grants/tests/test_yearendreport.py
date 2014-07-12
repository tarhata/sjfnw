from django.core import mail
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from django.utils import timezone

from sjfnw.constants import TEST_MIDDLEWARE
from sjfnw.grants import models
from sjfnw.grants.tests.base import BaseGrantTestCase

from datetime import timedelta
import json, unittest, logging
logger = logging.getLogger('sjfnw')

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class YearEndReportForm(BaseGrantTestCase):
  """ Test functionality related to the YER form:
      Views that handle autosave, file upload, submission
      Form validation with YER modelform """

  def setUp(self):
    super(YearEndReportForm, self).setUp(login='testy')
    today = timezone.now()
    award = models.GivingProjectGrant(projectapp_id = 1, amount = 5000,
        agreement_mailed = today - timedelta(days = 345),
        agreement_returned = today - timedelta(days = 350))
    award.save()
    self.award_id = award.pk

  def create_draft(self):
    # create the initial draft by visiting report page
    response = self.client.get('/report/%d' % self.award_id)
    self.assertEqual(1, models.YERDraft.objects.filter(award_id=self.award_id).count())

  def test_home_link(self):
    """ Load home page, verify it links to report """

    response = self.client.get('/apply/')

    self.assertTemplateUsed('grants/org_home.html')
    award = models.GivingProjectGrant.objects.get(projectapp_id=1)
    self.assertContains(response, '<a href="/report/%d">' % award.pk)

  def test_home_link_early(self):
    """ Verify link to report isn't shown if agreement hasn't been mailed """

    award = models.GivingProjectGrant.objects.get(projectapp_id=1)
    award.agreement_mailed = None
    award.save()

    response = self.client.get('/apply/')

    self.assertTemplateUsed('grants/org_home.html')
    award = models.GivingProjectGrant.objects.get(projectapp_id=1)
    self.assertNotContains(response, '<a href="/report/%d">' % award.pk)

  def test_late_home_link(self):
    """ Load home page, verify it links to report even if report is overdue """
    award = models.GivingProjectGrant.objects.get(projectapp_id=1)
    award.agreement_mailed = timezone.now() - timedelta(days = 400)
    award.save()

    response = self.client.get('/apply/')

    self.assertTemplateUsed('grants/org_home.html')
    award = models.GivingProjectGrant.objects.get(projectapp_id=1)
    self.assertContains(response, '<a href="/report/%d">' % award.pk)

  def test_start_report(self):
    """ Load report for first time """

    award = models.GivingProjectGrant.objects.get(projectapp_id=1)
    # no draft yet
    self.assertEqual(0, models.YERDraft.objects.filter(award_id=award.pk).count())

    response = self.client.get('/report/%d' % award.pk)

    self.assertTemplateUsed(response, 'grants/yer_form.html')
    # assert draft created
    self.assertEqual(1, models.YERDraft.objects.filter(award_id=award.pk).count())

    form = response.context['form']
    application = award.projectapp.application
    # assert website autofilled from app
    self.assertEqual(form['website'].value(), application.website)

  def test_autosave(self):

    self.create_draft()

    # send additional content to autosave
    post_data = {
        'summarize_last_year': 'We did soooooo much stuff last year!!',
        'goal_progress': 'What are goals?',
        'total_size': '546 or 547',
        'other_comments': 'All my single ladies'
        }

    response = self.client.post('/report/%d/autosave/' % self.award_id, post_data)
    self.assertEqual(200, response.status_code)
    draft = models.YERDraft.objects.get(award_id=self.award_id)
    self.assertEqual(json.loads(draft.contents), post_data)

  def test_valid_stay_informed(self):

    self.create_draft()

    post_data = {
      'other_comments': 'Some comments',
      'total_size': '500',
      'award': '55',
      'quantitative_measures': 'Measures',
      'major_changes': 'Changes',
      'twitter': '',
      'listserve': 'Yes this',
      'summarize_last_year': 'It was all right.',
      'newsletter': '',
      'other': '',
      'donations_count': '503',
      'user_id': '',
      'phone': '208-861-8907',
      'goal_progress': 'We haven\'t made much progress sorry.',
      'contact_person_1': 'Executive Board Co-Chair',
      'contact_person_0': 'Krista Perry',
      'new_funding': 'None! UGH.',
      'email': 'Idahossc@gmail.com',
      'facebook': '',
      'website': 'www.idahossc.org',
      'achieved': 'Achievement awards.'
    }


    # autosave the post_data (mimic page js which does that prior to submitting)
    response = self.client.post(reverse('sjfnw.grants.views.autosave_yer',
      kwargs = {'award_id': self.award_id}),
                                post_data)
    self.assertEqual(200, response.status_code)
    # confirm draft updated
    draft = models.YERDraft.objects.get(award_id = self.award_id)
    self.assertEqual(json.loads(draft.contents), post_data)
    # add files to draft
    draft.photo1 = 'cats.jpg'
    draft.photo2 = 'fiscal.png'
    draft.photo_release = 'budget1.docx'
    draft.save()

    # post
    response = self.client.post('report/%d' % self.award_id)

    self.assertTemplateUsed('grants/yer_submitted.html')

  def test_valid_late(self):
    """ Run the valid test but with a YER that is overdue """
    award = models.GivingProjectGrant.objects.get(projectapp_id=1)
    award.agreement_mailed = timezone.now() - timedelta(days = 400)
    award.save()

    self.test_valid_stay_informed()

  def test_start_late(self):
    """ Run the start draft test but with a YER that is overdue """
    award = models.GivingProjectGrant.objects.get(projectapp_id=1)
    award.agreement_mailed = timezone.now() - timedelta(days = 400)
    award.save()

    self.test_start_report()

@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class YearEndReportReminders(BaseGrantTestCase):
  """ Test reminder email functionality """

  projectapp_id = 1
  url = reverse('sjfnw.grants.views.yer_reminder_email')

  def setUp(self):
    super(YearEndReportReminders, self).setUp(login='admin')

  def test_two_months_prior(self):
    """ Verify reminder is not sent 2 months before report is due """

    # create award where yer should be due in 60 days
    today = timezone.now()
    mailed = today.date().replace(year = today.year - 1) + timedelta(days = 60)
    award = models.GivingProjectGrant(
        projectapp_id = 1, amount = 5000,
        agreement_mailed = mailed,
        agreement_returned = mailed + timedelta(days = 3)
    )
    award.save()
    print(models.GivingProjectGrant.objects.all())

    # verify that yer is due in 60 days
    self.assertEqual(award.yearend_due(), today.date() + timedelta(days = 60))

    # verify that email is not sent
    self.assertEqual(len(mail.outbox), 0)
    response = self.client.get(self.url)
    print(mail.outbox)
    self.assertEqual(len(mail.outbox), 0)

  def test_first_email(self):
    """ Verify that reminder email gets sent 30 days prior to due date """

    # create award where yer should be due in 30 days
    today = timezone.now()
    mailed = today.date().replace(year = today.year - 1) + timedelta(days = 30)
    award = models.GivingProjectGrant(
        projectapp_id = 1, amount = 5000,
        agreement_mailed = mailed,
        agreement_returned = mailed + timedelta(days = 3)
    )
    award.save()

    # verify that yer is due in 30 days
    self.assertEqual(award.yearend_due(), today.date() + timedelta(days = 30))

    # verify that email is not sent
    self.assertEqual(len(mail.outbox), 0)
    response = self.client.get(self.url)
    self.assertEqual(len(mail.outbox), 1)

  def test_15_days_prior(self):
    """ Verify that no email is sent 15 days prior to due date """

    # create award where yer should be due in 15 days
    today = timezone.now()
    mailed = today.date().replace(year = today.year - 1) + timedelta(days = 15)
    award = models.GivingProjectGrant(
        projectapp_id = 1, amount = 5000,
        agreement_mailed = mailed,
        agreement_returned = mailed + timedelta(days = 3)
    )
    award.save()
    print(models.GivingProjectGrant.objects.all())

    # verify that yer is due in 15 days
    self.assertEqual(award.yearend_due(), today.date() + timedelta(days = 15))

    # verify that email is not sent
    self.assertEqual(len(mail.outbox), 0)
    response = self.client.get(self.url)
    self.assertEqual(len(mail.outbox), 0)

  def test_second_email(self):
    """ Verify that a reminder email goes out 7 days prior to due date """

    # create award where yer should be due in 7 days
    today = timezone.now()
    mailed = today.date().replace(year = today.year - 1) + timedelta(days = 7)
    award = models.GivingProjectGrant(
        projectapp_id = 1, amount = 5000,
        agreement_mailed = mailed,
        agreement_returned = mailed + timedelta(days = 3)
    )
    award.save()

    # verify that yer is due in 7 days
    self.assertEqual(award.yearend_due(), today.date() + timedelta(days = 7))

    # verify that email is sent
    self.assertEqual(len(mail.outbox), 0)
    response = self.client.get(self.url)
    self.assertEqual(len(mail.outbox), 1)

  def test_yer_complete(self):
    """ Verify that an email is not sent if a year-end report has been completed """

    # create award where yer should be due in 7 days
    today = timezone.now()
    mailed = today.date().replace(year = today.year - 1) + timedelta(days = 7)
    award = models.GivingProjectGrant(
        projectapp_id = 1, amount = 5000,
        agreement_mailed = mailed,
        agreement_returned = mailed + timedelta(days = 3)
    )
    award.save()
    yer = models.YearEndReport(award = award, total_size=10, donations_count=50)
    yer.save()

    # verify that yer is due in 7 days
    self.assertEqual(award.yearend_due(), today.date() + timedelta(days = 7))

    # verify that email is not sent
    self.assertEqual(len(mail.outbox), 0)
    response = self.client.get(self.url)
    self.assertEqual(len(mail.outbox), 0)

class RolloverYER(BaseGrantTestCase):
  """ Test display and function of the rollover feature for YER """

  url = reverse('sjfnw.grants.views.rollover_yer')
  template_success = 'NAME'
  template_error = 'grants/yer_rollover.html'

  def setUp(self):
    super(RolloverYER, self).setUp(login='testy')

  def test_rollover_link(self):
    """ Verify that link shows on home page """

    response = self.client.get('/apply', follow=True)
    self.assertContains(response, 'rollover a year-end report')

  def test_display_no_awards(self):
    """ Verify correct error msg, no form, if org has no grants """

    self.logInNeworg()
    response = self.client.get(self.url, follow=True)
    self.assertEqual(response.context['error_msg'], 'You don\'t have any submitted reports to copy.')

  def test_display_no_reports(self):
    """ Verify error msg, no form if org has grant(s) but no reports """
    # Has 1+ grants
    award = models.GivingProjectGrant(projectapp_id=1, amount=8000)
    award.save()
    self.assertNotEqual(models.GivingProjectGrant.objects.filter(
      projectapp__application__organization_id=2).count(), 0)

    response = self.client.get(self.url, follow=True)
    self.assertEqual(response.context['error_msg'], 'You don\'t have any submitted reports to copy.')

  def test_display_all_reports_done(self):
    """ Verify error msg, no form if org has reports for all grants """
    award = models.GivingProjectGrant(projectapp_id = 1, amount = 5000)
    award.save()
    yer = models.YearEndReport(award = award, total_size=10, donations_count=50)
    yer.save()

    response = self.client.get(self.url, follow=True)
    self.assertEqual(response.context['error_msg'], 'You have a submitted or draft year-end report for all of your grants. <a href="/apply">Go back</a>')


  def test_display_form(self):
    """ Verify display of form when there is a valid rollover option """

    # create award and YER
    award = models.GivingProjectGrant(projectapp_id = 1, amount = 5000)
    award.save()
    yer = models.YearEndReport(award = award, total_size=10, donations_count=50)
    yer.save()

    # create 2nd award without YER
    papp = models.ProjectApp(application_id=2, giving_project_id=3)
    papp.save()
    mailed = timezone.now() - timedelta(days = 355)
    award = models.GivingProjectGrant(
        projectapp = papp, amount = 8000,
        agreement_mailed = mailed, 
        agreement_returned = mailed + timedelta(days = 3),
    )
    award.save()

    response = self.client.get(self.url, follow=True)
    print(response.context)
    self.assertNotIn('error_msg', response.context)

  @unittest.skip('Incomplete')
  def test_submit(self):
    """ Verify that rollover submit works:
      New draft is created for the selected award
      User is redirected to edit draft """

    # set up existing report + award without report
    self.test_display_form()

    post_data = {
      'report': '',
      'award': ''
    }
    


