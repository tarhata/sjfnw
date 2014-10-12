from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.conf import settings

from sjfnw.grants.models import Organization, GrantApplication

class Command(BaseCommand):

  help = ('Update org profiles.')

  def handle(self, *args, **kwargs):

    self.stdout.write('Using ' + settings.DATABASES['default']['NAME'])
    confirm = raw_input('Continue? (y/n) ')
    if confirm != 'y':
      self.stdout.write('Aborting')
      return

    orgs = Organization.objects.all()

    for org in orgs:
      apps = org.grantapplication_set.order_by('-submission_time');
      if len(apps) > 0:
        app = apps[0]
        for field in Organization._meta.get_all_field_names():
          if field != 'id' and hasattr(app, field):
            setattr(org, field, getattr(app, field))
        org.save()
        self.stdout.write('Updated organization profile for ' + org.name)
      else:
        self.stdout.write('Skipping %s, no applications submitted' % org.name)

    self.stdout.write('All org profiles updated.')

