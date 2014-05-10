from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):

  help = 'dump data from live site into fixtures'

  def handle(self, **args, **options):
    if settings.DATABASES['default']['NAME'] == 'sjfdb_local':
      self.stderr.write('Using local db.  Did you mean to load_testing_data?'
      return

    self.stdout.write('Pulling year end reports...')

    self.stdout.write('Pulling giving projects..')
    call_command('dumpdata', 'sjfnw/fund/fixtures/live_gp_dump.json')

    self.stdout.write('Pulling organizations..')
    call_command('dumpdata', 'sjfnw/grants/fixtures/orgs.json')

    self.stdout.write('Pulling grant cycles..')
    call_command('dumpdata', 'sjfnw/grants/fixtures/grant_cycles.json')

    self.stdout.write('Pulling applications..')
    call_command('dumpdata', 'sjfnw/grants/fixtures/apps.json')
    self.stdout.write('Pulling drafts..')
    call_command('dumpdata', 'sjfnw/grants/fixtures/drafts.json')

    self.stdout.write('Pulling projectapps..')
    call_command('dumpdata', 'sjfnw/grants/fixtures/project_apps.json')

    self.stdout.write('Pulling awards..')
    call_command('dumpdata', 'sjfnw/grants/fixtures/gp_grants.json')

    self.stdout.write('Pulling year-end reports..')
    call_command('dumpdata', 'sjfnw/grants/fixtures/project_apps.json')

    self.stdout.write('Pulling members..')
    call_command('dumpdata', 'sjfnw/fund/fixtures/live_member_dump.json')

    self.stdout.write('Pulling memberships..')
    call_command('dumpdata', 'sjfnw/fund/fixtures/live_membership_dump.json')

    self.stdout.write('Pulling donors..')
    call_command('dumpdata', 'sjfnw/fund/fixtures/live_donor_dump.json')

    self.stdout.write('Pulling steps..')
    call_command('dumpdata', 'sjfnw/fund/fixtures/live_step_dump.json')
