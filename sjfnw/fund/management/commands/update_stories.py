from django.core.management.base import BaseCommand
from django.utils import timezone
from sjfnw.fund.models import Step, Membership
import datetime

class Command(BaseCommand):

  help = 'Runs update story for missed days 6-13 to 6-14'

  def handle(self, *args, **options):
    self.stdout.write('Beginning.\n')
    start = datetime.datetime.strptime('2013-06-13 03:04:01',
                                       '%Y-%m-%d %H:%M:%S')
    start = timezone.make_aware(start, timezone.get_current_timezone())
    end = datetime.datetime.strptime('2013-06-14 05:06:01',
                                     '%Y-%m-%d %H:%M:%S')
    end = timezone.make_aware(end, timezone.get_current_timezone())
    # Get all memberships who completed a step within this range
    ships = (Step.objects.filter(completed__range=(start, end))
                        .values_list('donor__membership', flat=True)
                        .distinct())

    for ship_id in ships:
      try:
        ship = Membership.objects.get(id = ship_id)
      except:
        self.stderr.write('Trying to update story for non-existent member ' + unicode(ship_id))
      self.stdout.write('creating stories for ' + unicode(ship_id) + '\n')
      for i in range(0, 6):
        ship.update_story(start + datetime.timedelta(days=i))

    self.stdout.write('Script complete.\n')

