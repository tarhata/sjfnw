from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.conf import settings

from sjfnw.grants.models import GrantApplication, ProjectApp, GrantAward
from sjfnw.fund.models import GivingProject

class Command(BaseCommand):

  help = ('Verify that data has been updated properly before dropping any '
          'columns/tables')
  
  def print_success(self, text='success'):
    self.stdout.write('\033[00;32m' + text + '\033[00m')

  def print_fail(self, text):
    self.stderr.write(text)

  def handle(self, *args, **kwargs):
    self.stdout.write('Checking if all apps with GPs now have ProjectApps..')
    apps_count = GrantApplication.objects.exclude(giving_project__isnull=True).count()
    papps = ProjectApp.objects.all().select_related('application')
    papps_count = papps.count()
    if apps_count == papps_count:
      self.print_success()
    else:
      self.print_fail('%d apps with GPs, %d ProjectApps' % (apps_count, papps_count))

    self.stdout.write('Checking screening status and gp assignment match..')
    wrong = 0
    for papp in papps:
      if papp.screening_status != papp.application.screening_status:
        wrong += 1
      if papp.giving_project != papp.application.giving_project:
        wrong += 1
      if papp.application.pre_screening_status < 40:
        self.print_fail('Application assigned to GP with ss < 40')
    if wrong == 0:
      self.print_success()
    else:
      self.print_fail('%d mismatches between app and project app data' % wrong)

    self.stdout.write('Check if awards have been updated..')
    awards = GrantAward.objects.all().select_related(
      'application', 'project_app', 'project_app__appliation')
    wrong = 0
    for award in awards:
      if not award.project_app:
        self.print_fail('Award without projectapp #' + str(award.pk))
      elif award.application != award.project_app.application:
        wrong += 1
    if wrong == 0:
      self.print_success()
    else:
      self.print_fail('%d mismatches' % wrong)






