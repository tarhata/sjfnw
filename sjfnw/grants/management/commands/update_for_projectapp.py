from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.conf import settings

from sjfnw.grants.models import Organization, GrantApplication, ProjectApp, GivingProjectGrant
from sjfnw.fund.models import GivingProject


class Command(BaseCommand):

  help = ('Moves fields around from the old 1 GP per app setup to a new setup '
          'with a manytomany connection')

  def handle(self, *args, **kwargs):
    
    if settings.DATABASES['default']['NAME'] != 'sjfdb_local':
      opt_cont = input('You are using the live database.  Press 1 to continue')
      if opt_cont != '1':
        self.stdout.write('Terminating.')
        return

    # 1 syncdb to create the new tables
    self.stdout.write('Creating new tables...')
    call_command('syncdb')

    # for each app that's assigned to a gp, create a projectapp and copy
    # relevant fields there
    self.stdout.write('Restructing application - giving projects connections...')
    apps = GrantApplication.objects.filter(giving_project__isnull=False)
    connections = 0
    awards = 0
    for app in apps:
      project_app = ProjectApp(application = app,
                               giving_project = app.giving_project,
                               screening_status = app.screening_status)
      project_app.save()
      connections += 1
      awards = app.grantaward_set
      # if this app has awards, recreate them in new format
      if awards:
        award = awards[0]
        gpg = GivingProjectGrant(project_app = project_app,
                                 amount = award.amount,
                                 check_number = award.check_number,
                                 check_mailed = award.check_mailed,
                                 agreement_mailed = award.agreement_mailed,
                                 agreement_returned = award.agreement_returned,
                                 approved = award.approved)
        gpg.save()
        awards += 1

