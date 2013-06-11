from django.core.management.base import BaseCommand
from fund.models import Donor

class Command(BaseCommand):

  help = 'Fixes next step associations'

  def handle(self, *args, **options):
    self.stdout.write('Beginning.\n')
    for donor in Donor.objects.all():
      self.stdout.write(unicode(donor) + ' ' + str(donor.next_step is not None))
      steps = donor.step_set.filter(completed__isnull = True)
      if steps:
        donor.next_step = steps[0]
        self.stdout.write(' - next_step set\n')
      else:
        donor.next_step = None
        self.stdout.write(' - next_step None\n')
      donor.save()
    self.stdout.write('Script complete.')
