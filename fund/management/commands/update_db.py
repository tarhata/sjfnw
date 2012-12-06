from django.core.management.base import BaseCommand, CommandError
from fund.models import Donor, Step

class Command(BaseCommand):

  help = 'Not in use'

  def handle(self, *args, **options):
    self.stdout.write('This is empty.')