from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.conf import settings

from sjfnw.grants.models import Organization, GrantApplication, ProjectApp, GrantAward
from sjfnw.fund.models import GivingProject


class Command(BaseCommand):

  help = ('Moves fields around from the old 1 GP per app setup to a new setup '
          'with a manytomany connection')

  def handle(self, *args, **kwargs):

    if settings.DATABASES['default']['NAME'] != 'sjfdb_local':
      opt_cont = raw_input('You are using the live database.  Press y to continue: ')
      if opt_cont != 'y':
        self.stderr.write('Terminating.')
        return

    # 1 syncdb to create the new tables
    # self.stdout.write('Creating new tables...')
    # call_command('syncdb')

    # self.stdout.write('Deleting projectapps from previous fails..')
    # ProjectApp.objects.all().delete()

    # for each app that's assigned to a gp, create a projectapp and copy
    # relevant fields there
    self.stdout.write('Restructing application - giving projects connections...')
    apps = GrantApplication.objects.all()
    count_pa = 0
    count_a = 0
    for app in apps:
      app.pre_screening_status = app.screening_status
      app.save()
      if app.giving_project:
        project_app = ProjectApp(application = app,
                                 giving_project = app.giving_project)
        if app.screening_status > 50:
          project_app.screening_status = app.screening_status
        project_app.save()
        count_pa += 1

    awards = GrantAward.objects.all().select_related('application', 'application__giving_project')
    for award in awards:
      app = award.application
      gp = app.giving_project
      if not gp:
        self.stderr.write('Award whose app has no gp: award #' + str(award.pk))
      else:
        try:
          papp = ProjectApp.objects.get(application=app, giving_project=gp)
          award.project_app = papp
          award.save()
          count_a += 1
        except ProjectApp.DoesNotExist:
          self.stderr.write('No ProjectApp found for awarded app #' + str(app.pk))

    self.stdout.write('Done. %d intermediates created, %d awards updated.' % (count_pa, count_a))

