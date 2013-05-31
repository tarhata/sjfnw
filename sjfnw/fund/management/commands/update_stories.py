from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from fund.models import Donor, Step
import datetime

class Command(BaseCommand):

  help = 'Runs update story for missed days 5-21 to 5-28'
  
  def handle(self, *args, **options):
    self.stdout.write('Beginning.\n')
    start = datetime.datetime.strptime('2013-05-21 03:04:01', '%Y-%m-%d %H:%M:%S')
    start = timezone.make_aware(start, timezone.get_current_timezone())
    end = datetime.datetime.strptime('2013-05-28 05:06:01', '%Y-%m-%d %H:%M:%S')
    end = timezone.make_aware(end, timezone.get_current_timezone())
    #UpdateStory takes membership_id and timestamp, then searches all news/steps for that day
    #So we want all memberships who completed a step within this range
    ships = Step.objects.filter(completed__range=(start, end)).values_list('membership', flat=True)
    

    self.stdout.write('Script complete.')