from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.conf import settings

from sjfnw.grants.models import Organization, GrantApplication

class Command(BaseCommand):

  help = ('Update an organization\'s profile based on most recent grant app. '
          '(Use if changes have been made to app since submission)')

  def handle(self, *args, **kwargs):
    
    self.stdout.write('Using ' + settings.DATABASES['default']['NAME'])

    org_id = raw_input('Enter id of organization you wish to update: ')
    try:
      org_id = int(org_id)
    except:
      self.stderr.write('Invalid id')
      return

    try:
      org = Organization.objects.get(pk=org_id)
    except Organization.DoesNotExist:
      self.stderr.write('No organization found with id ' + str(org_id))
      return

    apps = GrantApplication.objects.filter(organization_id=org_id).order_by('-submission_time')

    try:
      app = apps[0]
    except:
      self.stderr.write('Organization has no grant applications')
      return

    self.stdout.write('Most recent app is ' + str(app))
    proceed = raw_input('Continue? (y/n) ')
    if proceed != 'y':
      self.stderr.write('Not modifying organization profile.')
      return

    for field in Organization._meta.get_all_field_names():
      if field != 'id' and hasattr(app, field):
        self.stdout.write('Setting ' + field)
        setattr(org, field, getattr(app, field))
    org.save()
    
    self.stdout.write('Updated organization profile.')
    
