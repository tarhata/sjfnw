from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.conf import settings

from sjfnw.grants.models import Organization
from sjfnw.fund.models import Member


class Command(BaseCommand):

  help = 'loads fixture data for manual testing purposes'

  def handle(self, *args, **options):
    if settings.DATABASES['default']['NAME'] != 'sjfdb_local':
      self.stderr.write('Error: This can only be used on the local database.')
      return

    # Minimal safety check
    if Organization.objects.count() > 0 or Member.objects.count() > 0:
      self.stderr.write('Error: Members or orgs exist. This is for use on an empty db.')
      return

    self.stdout.write('Loading grant cycles..')
    call_command('loaddata', 'sjfnw/grants/fixtures/grant_cycles.json')

    self.stdout.write('Loading organizations..')
    call_command('loaddata', 'sjfnw/grants/fixtures/orgs.json')

    self.stdout.write('Loading giving projects..')
    call_command('loaddata', 'sjfnw/fund/fixtures/live_gp_dump.json')

    self.stdout.write('Loading applications..')
    call_command('loaddata', 'sjfnw/grants/fixtures/apps.json')

    self.stdout.write('Loading projectapps..')
    call_command('loaddata', 'sjfnw/grants/fixtures/project_apps.json')

    self.stdout.write('Loading awards..')
    call_command('loaddata', 'sjfnw/grants/fixtures/gp_grants.json')

    self.stdout.write('Loading drafts..')
    call_command('loaddata', 'sjfnw/grants/fixtures/drafts.json')

    self.stdout.write('Loading members..')
    call_command('loaddata', 'sjfnw/fund/fixtures/live_member_dump.json')

    self.stdout.write('Loading memberships..')
    call_command('loaddata', 'sjfnw/fund/fixtures/live_membership_dump.json')

    self.stdout.write('Loading donors..')
    call_command('loaddata', 'sjfnw/fund/fixtures/live_donor_dump.json')

    self.stdout.write('Loading steps..')
    call_command('loaddata', 'sjfnw/fund/fixtures/live_step_dump.json')

    call_command('set_next_steps')

