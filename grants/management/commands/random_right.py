from django.core.management.base import BaseCommand, CommandError
from grants.models import *
import random
import hashlib
import datetime
from fund.models import GivingProject

def generate_string():
    return hashlib.md5(str(random.uniform(0, 1))).hexdigest()

def generate_grant_application():
    b = GivingProject()
    # b.organization = Grantee.objects.order_by('?')[0]
    b.grant_cycle = GrantCycle.objects.order_by('?')[0]

    b.fundraising_deadline = datetime.date.today()
    b.title = generate_string()
    return b;


class Command(BaseCommand):
    def handle(self, *args, **options):
        if len(args) != 1:
            print "Usage: python manage.py generate_grant_application n"
            print "Saves n grant applications"
        else:
            times = int(args[0])
            for times in range(0, times):
                grant_app = generate_grant_application()
                grant_app.save()
