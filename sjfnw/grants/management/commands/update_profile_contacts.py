from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from sjfnw.grants.models import Organization, GrantApplication

class Command(BaseCommand):

  help = 'Adds contact person & title to org profiles based on most recent app'

  def handle(self, *args, **kwargs):
    self.stdout.write('Fetching orgs..')
    orgs = Organization.objects.all()
    orgs_updated = 0
    orgs_left = 0
    for org in orgs:
      apps = org.grantapplication_set.order_by('-submission_time')
      if apps:
        org.contact_person = apps[0].contact_person
        org.contact_person_title = apps[0].contact_person_title
        org.save()
        orgs_updated += 1
        self.stdout.write('%s updated' % org.name)
      else:
        orgs_left += 1
        self.stdout.write('%s has no apps' % org.name)



    self.stdout.write('Script complete. %d orgs update, %d without apps left blank' % (orgs_updated, orgs_left))


