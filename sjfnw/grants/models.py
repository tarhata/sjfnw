from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import BaseValidator
from django.db import models
from django.utils import timezone

from sjfnw.fund.models import GivingProject
from sjfnw import constants

from datetime import timedelta
import logging, json, re

logger = logging.getLogger('sjfnw')


#used by org & app
STATE_CHOICES = [
  ('ID', 'ID'),
  ('MT', 'MT'),
  ('OR', 'OR'),
  ('WA', 'WA'),
  ('WY', 'WY'),

  ('AL', 'AL'),
  ('AK', 'AK'),
  ('AZ', 'AZ'),
  ('AR', 'AR'),
  ('CA', 'CA'),
  ('CO', 'CO'),
  ('CT', 'CT'),
  ('DE', 'DE'),
  ('FL', 'FL'),
  ('GA', 'GA'),
  ('HI', 'HI'),
  ('IL', 'IL'),
  ('IN', 'IN'),
  ('IA', 'IA'),
  ('KS', 'KS'),
  ('KY', 'KY'),
  ('LA', 'LA'),
  ('ME', 'ME'),
  ('MD', 'MD'),
  ('MA', 'MA'),
  ('MI', 'MI'),
  ('MN', 'MN'),
  ('MS', 'MS'),
  ('MO', 'MO'),
  ('NE', 'NE'),
  ('NV', 'NV'),
  ('NH', 'NH'),
  ('NJ', 'NJ'),
  ('NM', 'NM'),
  ('NY', 'NY'),
  ('NC', 'NC'),
  ('ND', 'ND'),
  ('OH', 'OH'),
  ('OK', 'OK'),
  ('PA', 'PA'),
  ('RI', 'RI'),
  ('SC', 'SC'),
  ('SD', 'SD'),
  ('TN', 'TN'),
  ('TX', 'TX'),
  ('UT', 'UT'),
  ('VT', 'VT'),
  ('VA', 'VA'),
  ('WV', 'WV'),
  ('WI', 'WI')]

STATUS_CHOICES = [
  ('Tribal government',
   'Federally recognized American Indian tribal government'),
  ('501c3', '501(c)3 organization as recognized by the IRS'),
  ('501c4', '501(c)4 organization as recognized by the IRS'),
  ('Sponsored',
   'Sponsored by a 501(c)3, 501(c)4, or federally recognized tribal government')
  ]

PRE_SCREENING = (
  (10, 'Received'),
  (20, 'Incomplete'),
  (30, 'Complete'),
  (40, 'Pre-screened out'),
  (45, 'Screened out by sub-committee'),
  (50, 'Pre-screened in')
)

SCREENING = (
  (60, 'Screened out'),
  (70, 'Site visit awarded'), #site visit reports
  (80, 'Grant denied'),
  (90, 'Grant issued'),
  (100, 'Grant paid'),
  (110, 'Year-end report overdue'),
  (120, 'Year-end report received'),
  (130, 'Closed')
)

class Organization(models.Model):
  #registration fields
  name = models.CharField(max_length=255, unique=True, error_messages={
    'unique': ('An organization with this name is already in the system. '
    'To add a separate org with the same name, add/alter the name to '
    'differentiate the two.')})
  email = models.EmailField(max_length=100, verbose_name='Login',
                            blank=True, unique=True) #django username

  #org contact info
  address = models.CharField(max_length=100, blank=True)
  city = models.CharField(max_length=50, blank=True)
  state = models.CharField(max_length=2, choices=STATE_CHOICES, blank=True)
  zip = models.CharField(max_length=50, blank=True)
  telephone_number = models.CharField(max_length=20, blank=True)
  fax_number = models.CharField(max_length=20, blank=True)
  email_address = models.EmailField(max_length=100, blank=True)
  website = models.CharField(max_length=50, blank=True)
  contact_person = models.CharField(max_length=250, blank=True,
      verbose_name= 'Contact person')
  contact_person_title = models.CharField(max_length=100, blank=True,
      verbose_name='Title')

  #org info
  status = models.CharField(max_length=50, choices=STATUS_CHOICES, blank=True)
  ein = models.CharField(max_length=50,
                         verbose_name="Organization's or Fiscal Sponsor Organization's EIN",
                         blank=True)
  founded = models.PositiveIntegerField(verbose_name='Year founded',
                                        null=True, blank=True)
  mission = models.TextField(blank=True)

  #fiscal sponsor info (if applicable)
  fiscal_org = models.CharField(verbose_name='Organization name',
                                max_length=255, blank=True)
  fiscal_person = models.CharField(verbose_name='Contact person',
                                   max_length=255, blank=True)
  fiscal_telephone = models.CharField(verbose_name='Telephone',
                                      max_length=25, blank=True)
  fiscal_email = models.CharField(verbose_name='Email address',
                                  max_length=100, blank=True)
  fiscal_address = models.CharField(verbose_name='Address',
                                    max_length=255, blank=True)
  fiscal_city = models.CharField(verbose_name='City',
                                 max_length=50, blank=True)
  fiscal_state = models.CharField(verbose_name='State', max_length=2,
                                  choices=STATE_CHOICES, blank=True)
  fiscal_zip = models.CharField(verbose_name='ZIP', max_length=50, blank=True)
  fiscal_letter = models.FileField(upload_to='/', null=True, blank=True)

  def __unicode__(self):
    return self.name

  class Meta:
    ordering = ('name',)

class GrantCycle(models.Model):
  title = models.CharField(max_length=100)
  open = models.DateTimeField()
  close = models.DateTimeField()
  extra_question = models.TextField(blank=True)
  info_page = models.URLField()
  email_signature = models.TextField(blank=True)
  conflicts = models.TextField(blank=True,
      help_text='Track any conflicts of interest (automatic & personally '
      'declared) that occurred  during this cycle.')

  class Meta:
    ordering = ['title', 'close']

  def __unicode__(self):
    return self.title

  def is_open(self):
    return (self.open < timezone.now() < self.close)

  def get_status(self):
    today = timezone.now()
    if self.close < today:
      return 'closed'
    elif self.open > today:
      return 'upcoming'
    else:
      return 'open'

class DraftGrantApplication(models.Model):
  """ Autosaved draft application """

  organization = models.ForeignKey(Organization)
  grant_cycle = models.ForeignKey(GrantCycle)
  created = models.DateTimeField(blank=True, default = timezone.now())
  modified = models.DateTimeField(blank=True, default = timezone.now())
  modified_by = models.CharField(blank=True, max_length=100)

  contents = models.TextField(default='{}')

  budget = models.FileField(upload_to='/', max_length=255)
  demographics = models.FileField(upload_to='/', max_length=255)
  funding_sources = models.FileField(upload_to='/', max_length=255)
  budget1 = models.FileField(upload_to='/', max_length=255,
                             verbose_name = 'Annual statement')
  budget2 = models.FileField(upload_to='/', max_length=255,
                             verbose_name = 'Annual operating')
  budget3 = models.FileField(upload_to='/', max_length=255,
                             verbose_name = 'Balance sheet')
  project_budget_file = models.FileField(upload_to='/', max_length=255,
                                         verbose_name = 'Project budget')
  fiscal_letter = models.FileField(upload_to='/', max_length=255)

  extended_deadline = models.DateTimeField(help_text = ('Allows this draft to'
                                           ' be edited/submitted past the grant'
                                           ' cycle close.'),
                                           blank=True, null=True)

  class Meta:
    unique_together = ('organization', 'grant_cycle')

  def __unicode__(self):
    return u'DRAFT: ' + self.organization.name + ' - ' + self.grant_cycle.title

  def overdue(self):
    return self.grant_cycle.close <= timezone.now()

  def editable(self):
    deadline = self.grant_cycle.close
    logger.debug('deadline is ' + str(self.grant_cycle.close))
    now = timezone.now()
    if self.grant_cycle.open < now and (deadline > now or 
        (self.extended_deadline and self.extended_deadline > now)):
      return True
    else:
      return False

  @classmethod
  def file_fields(cls):
    return [f.name for f in cls._meta.fields if isinstance(f, models.FileField)]

class WordLimitValidator(BaseValidator):
  compare = lambda self, a, b: a > b
  clean   = lambda self, x: len(re.findall(r'[^ \n\r]+', x))
  message = (u'Ensure this value has at most %(limit_value)d words '
             '(it has %(show_value)d).')
  code = 'max_words'

def validate_file_extension(value):
  if not value.name.lower().split(".")[-1] in constants.ALLOWED_FILE_TYPES:
    raise ValidationError(u'That file type is not supported.')

class GrantApplication(models.Model):
  """ Submitted grant application """

  #automated fields
  submission_time = models.DateTimeField(blank=True, default=timezone.now(),
                                         verbose_name='Submitted')
  organization = models.ForeignKey(Organization)
  grant_cycle = models.ForeignKey(GrantCycle)

  #contact info
  address = models.CharField(max_length=100)
  city = models.CharField(max_length=50)
  state = models.CharField(max_length=2, choices=STATE_CHOICES)
  zip = models.CharField(max_length=50)
  telephone_number = models.CharField(max_length=20)
  fax_number = models.CharField(max_length=20, blank=True,
                                verbose_name = 'Fax number (optional)',
                                error_messages={'invalid': u'Enter a 10-digit fax number (including area code).'})
  email_address = models.EmailField(max_length=100)
  website = models.CharField(max_length=50, blank=True,
                             verbose_name = 'Website (optional)')

  #org info
  status = models.CharField(max_length=50, choices=STATUS_CHOICES)
  ein = models.CharField(max_length=50,
                         verbose_name="Organization or Fiscal Sponsor EIN")
  founded = models.PositiveIntegerField(verbose_name='Year founded')
  mission = models.TextField(verbose_name="Mission statement",
                             validators=[WordLimitValidator(150)])
  previous_grants = models.CharField(max_length=255, blank=True,
      verbose_name='Previous SJF grants awarded (amounts and year)')

  #budget info
  start_year = models.CharField(max_length=250,
                                verbose_name='Start date of fiscal year')
  budget_last = models.PositiveIntegerField(verbose_name='Org. budget last fiscal year')
  budget_current = models.PositiveIntegerField(verbose_name='Org. budget this fiscal year')

  #this grant info
  grant_request = models.TextField(verbose_name="Briefly summarize the grant request",
                                   validators=[WordLimitValidator(100)])
  contact_person = models.CharField(max_length=250, verbose_name= 'Name',
                                    help_text='Contact person for this grant application')
  contact_person_title = models.CharField(max_length=100, verbose_name='Title')
  grant_period = models.CharField(max_length=250, blank=True,
                                  verbose_name='Grant period (if different than fiscal year)')
  amount_requested = models.PositiveIntegerField()

  SUPPORT_CHOICES = [('General support', 'General support'),
                     ('Project support', 'Project support'),]
  support_type = models.CharField(max_length=50, choices=SUPPORT_CHOICES)
  project_title = models.CharField(max_length=250, blank=True,
                                   verbose_name='Project title (if applicable)')
  project_budget = models.PositiveIntegerField(null=True, blank=True,
                                               verbose_name='Project budget (if applicable)')

  #fiscal sponsor
  fiscal_org = models.CharField(verbose_name='Fiscal org. name',
                                max_length=255, blank=True)
  fiscal_person = models.CharField(verbose_name='Contact person',
                                   max_length=255, blank=True)
  fiscal_telephone = models.CharField(verbose_name='Telephone',
                                      max_length=25, blank=True)
  fiscal_email = models.CharField(verbose_name='Email address',
                                  max_length=70, blank=True)
  fiscal_address = models.CharField(verbose_name='Address',
                                    max_length=255, blank=True)
  fiscal_city = models.CharField(verbose_name='City', max_length=50, blank=True)
  fiscal_state = models.CharField(verbose_name='State', max_length=2,
                                  choices=STATE_CHOICES, blank=True)
  fiscal_zip = models.CharField(verbose_name='ZIP', max_length=50, blank=True)

  #narratives
  NARRATIVE_CHAR_LIMITS = [0, 300, 150, 450, 300, 300, 450, 500]
  NARRATIVE_TEXTS = ['Placeholder for 0',
    ('Describe your organization\'s mission, history and major '
     'accomplishments.'), #1
    ('Social Justice Fund prioritizes groups that are led by the people most '
     'impacted by the issues the group is working on, and continually build '
     'leadership from within their own communities.<ul><li>Who are the '
     'communities most directly impacted by the issues your organization '
     'addresses?</li><li>How are those communities involved in the leadership '
     'of your organization, and how does your organization remain accountable '
     'to those communities?</li></ul>'), #2
    ('Social Justice Fund prioritizes groups that understand and address the '
    'underlying, or root causes of the issues, and that bring people together '
    'to build collective power.<ul><li>What problems, needs or issues does '
    'your work address?</li><li>What are the root causes of these issues?</li>'
    '<li>How does your organization build collective power?</li><li>How will '
    'your work change the root causes and underlying power dynamics of the '
    'identified problems, needs or issues?</li></ul>'), #3
    ('Please describe your workplan, covering at least the next 12 months. '
     '(You will list the activities and objectives in the timeline form below '
     'the narrative.)<ul><li>What are your overall goals and strategies for '
     'the coming year?</li><li>How will you assess whether you have met your '
     'objectives and goals?</li></ul>'), #4
    ('Social Justice Fund prioritizes groups that see themselves as part of a '
     'larger movement for social change, and work towards strengthening that '
     'movement.<ul><li>Describe at least two coalitions, collaborations, '
     'partnerships or networks that you participate in as an approach to '
     'social change.</li><li>What are the purposes and impacts of these '
     'collaborations?</li><li>What is your organization\'s role in these '
     'collaborations?</li><li>If your collaborations cross issue or '
     'constituency lines, how will this will help build a broad, unified, and '
     'effective progressive movement?</li></ul>'), #5
    ('Social Justice Fund prioritizes groups working on racial justice, '
     'especially those making connections between racism, economic injustice, '
     'homophobia, and other forms of oppression. Tell us how your organization '
     'is working toward racial justice and how you are drawing connections to '
     'economic injustice, homophobia, and other forms of oppression. <i>While '
     'we believe people of color must lead the struggle for racial justice, '
     'we also realize that the demographics of our region make the work of '
     'white anti-racist allies critical to achieving racial justice.</i> If '
     'you are a primarily white-led organization, also describe how you work '
     'as an ally to communities of color.') #6
  ]
  narrative1 = models.TextField(validators=[WordLimitValidator(NARRATIVE_CHAR_LIMITS[1])],
                                verbose_name = NARRATIVE_TEXTS[1])
  narrative2 = models.TextField(validators=[WordLimitValidator(NARRATIVE_CHAR_LIMITS[2])],
                                verbose_name = NARRATIVE_TEXTS[2])
  narrative3 = models.TextField(validators=[WordLimitValidator(NARRATIVE_CHAR_LIMITS[3])],
                                verbose_name = NARRATIVE_TEXTS[3])
  narrative4 = models.TextField(validators=[WordLimitValidator(NARRATIVE_CHAR_LIMITS[4])],
                                verbose_name = NARRATIVE_TEXTS[4])
  narrative5 = models.TextField(validators=[WordLimitValidator(NARRATIVE_CHAR_LIMITS[5])],
                                verbose_name = NARRATIVE_TEXTS[5])
  narrative6 = models.TextField(validators=[WordLimitValidator(NARRATIVE_CHAR_LIMITS[6])],
                                verbose_name = NARRATIVE_TEXTS[6])
  cycle_question = models.TextField(validators=[WordLimitValidator(NARRATIVE_CHAR_LIMITS[7])],
                                    blank=True)

  timeline = models.TextField()

  #collab references (after narrative 5)
  collab_ref1_name = models.CharField(help_text='Provide names and contact information for two people '
                                      'who are familiar with your organization\'s role in these '
                                      'collaborations so we can contact them for more information.',
                                      verbose_name='Name', max_length=150)
  collab_ref1_org = models.CharField(verbose_name='Organization',
                                     max_length=150)
  collab_ref1_phone = models.CharField(verbose_name='Phone number',
                                       max_length=20, blank=True)
  collab_ref1_email = models.EmailField(max_length=100, verbose_name='Email',
                                        blank=True)

  collab_ref2_name = models.CharField(verbose_name='Name', max_length=150)
  collab_ref2_org = models.CharField(verbose_name='Organization',
                                     max_length=150)
  collab_ref2_phone = models.CharField(verbose_name='Phone number',
                                       max_length=20, blank=True)
  collab_ref2_email = models.EmailField(max_length=100, verbose_name='Email',
                                        blank=True)

  #racial justice references (after narrative 6)
  racial_justice_ref1_name = models.CharField(help_text='If you are a primarily white-led organization, please list at least one organization led by people of color that we can contact as a reference for your racial justice work.', verbose_name='Name', max_length=150, blank=True)
  racial_justice_ref1_org = models.CharField(verbose_name='Organization',
                                             max_length=150, blank=True)
  racial_justice_ref1_phone = models.CharField(verbose_name='Phone number',
                                               max_length=20, blank=True)
  racial_justice_ref1_email = models.EmailField(verbose_name='Email',
                                                max_length=100, blank=True)

  racial_justice_ref2_name = models.CharField(verbose_name='Name',
                                              max_length = 150, blank=True)
  racial_justice_ref2_org = models.CharField(verbose_name='Organization',
                                             max_length = 150, blank=True)
  racial_justice_ref2_phone = models.CharField(verbose_name='Phone number',
                                               max_length = 20, blank=True)
  racial_justice_ref2_email = models.EmailField(verbose_name='Email',
                                                max_length=100, blank=True)

  #files
  budget = models.FileField(upload_to='/', max_length=255, validators=[validate_file_extension], blank=True)
  demographics = models.FileField(verbose_name = 'Diversity chart', upload_to='/', max_length=255, validators=[validate_file_extension])
  funding_sources = models.FileField(upload_to='/', max_length=255, validators=[validate_file_extension])
  budget1 = models.FileField(upload_to='/', max_length=255, verbose_name = 'Annual statement', validators=[validate_file_extension], blank=True)
  budget2 = models.FileField(upload_to='/', max_length=255, verbose_name = 'Annual operating budget', validators=[validate_file_extension], blank=True)
  budget3 = models.FileField(upload_to='/', max_length=255, verbose_name = 'Balance sheet (if available)', validators=[validate_file_extension], blank=True)
  project_budget_file = models.FileField(upload_to='/', max_length=255, verbose_name = 'Project budget (if applicable)', validators=[validate_file_extension], blank=True)
  fiscal_letter = models.FileField(upload_to='/', blank=True, verbose_name = 'Fiscal sponsor letter', help_text='Letter from the sponsor stating that it agrees to act as your fiscal sponsor and supports Social Justice Fund\'s mission.', max_length=255, validators=[validate_file_extension])

  # admin fields
  pre_screening_status = models.IntegerField(choices = PRE_SCREENING,
                                             default = 10)
  giving_projects = models.ManyToManyField(GivingProject, through='ProjectApp',
                                           blank=True)
  scoring_bonus_poc = models.BooleanField(default=False,
      verbose_name='Scoring bonus for POC-led')
  scoring_bonus_geo = models.BooleanField(default=False,
      verbose_name='Scoring bonus for geographic diversity')
  site_visit_report = models.URLField(
      blank=True, help_text = ('Link to the google doc containing the site '
      'visit report. This will be visible to all project members, but not the '
      'organization.'))

  class Meta:
    ordering = ['organization', 'submission_time']
    unique_together = ('organization', 'grant_cycle')

  def __unicode__(self):
    return unicode(self.organization) + u' - ' + unicode(self.grant_cycle) + u' - ' + unicode(self.submission_time.year)

  def id_number(self):
    return self.pk + 5211 #TODO obsolete?

  def view_link(self):
    return '<a href="/grants/view/' + str(self.pk) + '" target="_blank">View application</a>'
  view_link.allow_tags = True

  def timeline_display(self): #TODO move to modelform?
    logger.info(type(self.timeline))
    timeline = json.loads(self.timeline)
    html = '<table id="timeline_display"><tr class="heading"><td></td><th>date range</th><th>activities</th><th>goals/objectives</th></tr>'
    for i in range(0, 15, 3):
      html += '<tr><th class="left">q' + str((i+3)/3) + '</th><td>' + timeline[i] + '</td><td>' + timeline[i+1] + '</td><td>' + timeline[i+2] +'</td></tr>'
    html += '</table>'
    return html
  timeline_display.allow_tags = True

  @classmethod
  def get_field_names(cls):
    return [f for f in cls._meta.get_all_field_names()]

  @classmethod
  def fields_starting_with(cls, start):
    return [f for f in cls._meta.get_all_field_names() if f.startswith(start)]

  @classmethod
  def file_fields(cls):
    return [f.name for f in cls._meta.fields if isinstance(f, models.FileField)]


class ProjectApp(models.Model):
  """ Connection between a grant app and a giving project.

  Stores that project's screening and site visit info related to the app """

  giving_project = models.ForeignKey(GivingProject)
  application = models.ForeignKey(GrantApplication)

  screening_status = models.IntegerField(choices=SCREENING, blank=True,
                                         null=True)

  def __unicode__(self):
    return '%s - %s' % (self.giving_project.title, self.application)


class GrantApplicationLog(models.Model):
  date = models.DateTimeField(default = timezone.now())
  organization = models.ForeignKey(Organization)
  application = models.ForeignKey(GrantApplication, null=True, blank=True, help_text = 'Optional - if this log entry relates to a specific grant application, select it from the list')
  staff = models.ForeignKey(User)
  contacted = models.CharField(max_length=255, help_text = 'Person from the organization that you talked to, if applicable.', blank=True)
  notes = models.TextField()


class GivingProjectGrant(models.Model):
  created = models.DateTimeField(default=timezone.now())

  project_app = models.OneToOneField(ProjectApp)

  amount = models.DecimalField(max_digits=8, decimal_places=2)
  check_number = models.PositiveIntegerField(null=True, blank=True)
  check_mailed = models.DateField(null=True, blank=True)

  agreement_mailed = models.DateField(null=True, blank=True)
  agreement_returned = models.DateField(null=True, blank=True)
  approved = models.DateField(verbose_name='Date approved by the ED', null=True, blank=True)

  def agreement_due(self):
    if self.agreement_mailed:
      return self.agreement_mailed + timedelta(days=30)
    else:
      return None

  def yearend_due(self):
    if self.agreement_mailed:
      return (self.agreement_mailed +
          timedelta(days=30)).replace(year = self.agreement_mailed.year + 1)
    else:
      return None


class SponsoredProgramGrant(models.Model):

  entered = models.DateTimeField(default=timezone.now())
  organization = models.ForeignKey(Organization)
  amount = models.PositiveIntegerField()
  check_number = models.PositiveIntegerField(null=True, blank=True)
  check_mailed = models.DateField(null=True, blank=True)
  approved = models.DateField(verbose_name='Date approved by the ED',
                              null=True, blank=True)

  description = models.TextField(blank=True)

  class Meta:
    ordering = ['organization']

