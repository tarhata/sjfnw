from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from sjfnw.fund.models import Member
from sjfnw.grants.models import Organization

class Command(BaseCommand):

  help = 'Adds first and last names to User objects based on matching Member or Organization'

  def handle(self, *args, **kwargs):
    self.stdout.write('Checking users..')
    users_updated = 0
    users = User.objects.filter(first_name='', last_name='', is_staff=False)
    for user in users:
      try:
        member = Member.objects.get(email = user.username)
        self.stdout.write('Adding Member name to ' + user.username)
        user.last_name = member.last_name
        user.first_name = member.first_name
        user.save()
        users_updated += 1
      except Member.DoesNotExist:
        try:
          org = Organization.objects.get(email = user.username)
          self.stdout.write('Adding Org name to ' + user.username)
          user.first_name = org.name if len(org.name) <= 30 else (org.name[:28] + '..')
          user.last_name = '(organization)'
          user.save()
          users_updated += 1
        except Organization.DoesNotExist:
          self.stdout.write('No member or org found for ' + user.username)

    self.stdout.write('Script complete. ' + str(users_updated) +
        ' users updated; ' + str(len(users) - users_updated) + ' left blank.')


