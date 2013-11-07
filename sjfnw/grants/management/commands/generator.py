from django.core.management.base import BaseCommand
from django.utils import timezone

from sjfnw.fund.models import GivingProject
from sjfnw.grants import models

from datetime import timedelta
from random import randint
import string, json

#updated 4/28/13

class Command(BaseCommand):

  help = 'Generates fake grant applications.'

  def handle(self, *args, **options):#wrapper for sub-functions
    self.stdout.write('Starting process for generating fake apps\n')
    self.now = timezone.now()
    generate_cycles(self)
    generate_organizations(self)
    generate_giving_projects(self)
    generate_applications(self)

TZ = timezone.get_current_timezone()
GP_PREFIXES = ['LGBTQ', 'Montana', 'General', 'Economic Justice',
               'Environmental Justice', 'Criminal Justice']
GPS = [] #gp objects, to save queries

def generate_cycles(self): # 6
  if models.GrantCycle.objects.count() > 3:
    self.stdout.write('>=3 cycles exist, skipping.\n')
    return
  for name in GP_PREFIXES:
    open = self.now - timedelta(weeks=randint(1, 260))
    cycle = models.GrantCycle(title = name + ' Grant Cycle', open = open,
                              close = open + timedelta(weeks=7),
                              info_page = 'http://www.socialjusticefund.org/grant-app/lgbtq-grant-cycle')
    cycle.save()
  self.stdout.write('Cycles created\n')

def generate_organizations(self): # 17
  if models.Organization.objects.filter(name__startswith='Indian'):
    self.stdout.write('Auto-generated org found, skipping.\n')
    return
  a = ['Indian ', 'Gender ', 'API ', 'Equality ', 'Food ']
  b = ['Justice ', 'Community ', 'Action ', 'Rights ', 'Policy ']
  c = ['Foundation', 'Alliance', 'Network', 'Services', 'Center']
  #shuffle(a)
  #shuffle(b)
  #shuffle(c)
  for i in range(0, 4): #5
    name = a[i] + b[i] + c[i]
    org = models.Organization(name=name, email=name.lower().replace(' ', '_') + '@gmail.com')
    org.save()
  for i in range(0, 3): #12
    name = a[i] + b[i] + c[i+1]
    org = models.Organization(name=name, email=name.lower().replace(' ', '_') + '@gmail.com')
    org.save()
    name = a[i] + b[i+1] + c[i]
    org = models.Organization(name=name, email=name.lower().replace(' ', '_') + '@gmail.com')
    org.save()
    name = a[i] + b[i+1] + c[i+1]
    org = models.Organization(name=name, email=name.lower().replace(' ', '_') + '@gmail.com')
    org.save()
  self.stdout.write('Orgs created\n')

def generate_giving_projects(self): # 6
  if models.GrantCycle.objects.count() > 3:
    self.stdout.write('>=3 gps found, skipping.\n')
    return
  for name in GP_PREFIXES:
    gp = GivingProject(title = name + ' Giving Project',
                       fundraising_deadline = self.now,
                       fundraising_training = self.now)
    gp.save()
    GPS.append(gp)
  self.stdout.write('Giving Projects created\n')

def generate_applications(self):
  rl = models.GrantApplication.objects.filter()
  if not rl:
    self.stderr.write('Need at least one grant application in the database, '
                      'to steal file fields from\n')
    return
  rl = rl[0]
  for cycle in models.GrantCycle.objects.all():
    count = 0
    for org in models.Organization.objects.all():
      if randint(1, 100) > 59: #~60% chance
        app = models.GrantApplication(organization=org, grant_cycle=cycle)
        app.submission_time = self.now - timedelta(days=randint(1, 40))
        app.address = '1904 3rd Ave.'
        app.city = random_letters(8)
        app.state = models.STATE_CHOICES[randint(0, 4)][0]
        app.zip = '89568'
        app.telephone_number = random_phone()
        app.fax_number = random_phone()
        app.email_address = random_email()
        app.website = random_url()
        app.status = models.STATUS_CHOICES[randint(0, 3)][0]
        app.ein = str(randint(1230934, 9384743))
        app.founded = str(randint(1975, 2012))
        app.mission = random_words(600)
        app.previous_grants = 'None'
        app.start_year = 'Jan 1'
        app.budget_last = randint(2000, 50459)
        app.budget_current = randint(2000, 50459)
        app.grant_request = random_words(350)
        app.contact_person = random_words(12)
        app.contact_person_title = 'Executive Director'
        #app.grant_period
        app.amount_requested = 10000
        app.support_type = 'General'

        app.narrative1 = random_words(100)
        app.narrative2 = random_words(100)
        app.narrative3 = random_words(100)
        app.narrative4 = random_words(100)
        app.narrative5 = random_words(100)
        app.narrative6 = random_words(100)
        #app.cycle_question
        app.timeline = json.dumps(["Jan", "Chillin", "Not applicable", "Feb", "Petting dogs", "5 dogs", "Mar", "Planting daffodils", "s", "July", "Walking around Greenlake", "9 times", "August", "Reading in the shade", "No sunburns"])

        app.collab_ref1_name = random_words(25)
        app.collab_ref1_org = random_words(25)
        app.collab_ref1_phone = random_phone()
        app.collab_ref1_email = random_email()
        app.collab_ref2_name = random_words(25)
        app.collab_ref2_org = random_words(25)
        app.collab_ref2_phone = random_phone()
        app.collab_ref2_email = random_email()

        #skipping rj refs

        app.budget = rl.budget
        app.demographics = rl.demographics
        app.funding_sources = rl.funding_sources
        app.budget1 = rl.budget1
        app.budget2 = rl.budget2
        app.budget3 = rl.budget3

        app.screening_status = models.GrantApplication.SCREENING_CHOICES[randint(0, 12)][0]
        app.giving_project = models.GivingProject.objects.order_by('?')[0]
        if randint(1, 10) > 5:
          app.scoring_bonus_poc = True
        else:
          app.scoring_bonus_poc = False
        if randint(1, 10) > 6:
          app.scoring_bonus_geo = True
        else:
          app.scoring_bonus_geo = False

        app.save()
        count += 1
    self.stdout.write(str(count) + ' applications created for '+
                      unicode(cycle) + '\n')
  self.stdout.write('Application creation complete')

def random_phone():
  ph = ''
  for i in range(0, 10):
    ph += str(randint(1, 9))
  return ph[:3] + u'-' + ph[3:6] + u'-' + ph[6:]

def random_url():
  suf = ['.com', 'org', '.net', '.edu']
  return random_letters(12) + suf[randint(0, 3)]

def random_email():
  suf = ['@gmail.com', '@hotmail.com', '@yahoo.com']
  return random_letters(8) + suf[randint(0, 2)]

def random_letters(length):
  return random_string(length, False)

def random_words(length, case='sentence'):
  return random_string(length, True)

def random_string(length, spaces):
  chars = string.ascii_lowercase
  if spaces:
    chars += ' '
  le = len(chars)
  str = ''
  for i in range(0, length):
    str += chars[randint(0, le-1)]
  return str

