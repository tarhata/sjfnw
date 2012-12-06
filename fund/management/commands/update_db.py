from django.core.management.base import BaseCommand, CommandError
from fund.models import Donor, Step

class Command(BaseCommand):

  help = 'Fills in the next_step field on Donor models using get_next_step method'

  def handle(self, *args, **options):
    self.stdout.write('Beginning donor scan.\n')
    donors = Donor.objects.all()
    for donor in donors:
      next = donor.get_next_step()
      if next:
        donor.next_step = next
        donor.save()
        self.stdout.write('Next step set for ' + str(donor) + '\n')
      else:
        self.stdout.write(str(donor) + ' has no next step\n')

    self.stdout.write('All donors updated.')