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
  
  staff_contact_person = models.CharField(max_length=250, blank=True,
      verbose_name= 'Staff-entered contact person')
  staff_contact_person_title = models.CharField(max_length=100, blank=True,
      verbose_name='Title')
  staff_contact_email = models.EmailField(verbose_name='Email address',
      max_length=255, blank=True)
  staff_contact_phone = models.CharField(verbose_name='Phone number',
      max_length=20, blank=True)

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
  fiscal_letter = models.FileField(upload_to='/', null=True, blank=True, max_length=255)

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
    ordering = ['-close', 'title']

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
  created = models.DateTimeField(blank=True, default = timezone.now)
  modified = models.DateTimeField(blank=True, default = timezone.now)
  modified_by = models.CharField(blank=True, max_length=100)

  contents = models.TextField(default='{}')

  demographics = models.FileField(upload_to='/', max_length=255)
  funding_sources = models.FileField(upload_to='/', max_length=255)
  budget1 = models.FileField(upload_to='/', max_length=255,
                             verbose_name = 'Annual statement')
  budget2 = models.FileField(
      upload_to='/', max_length=255, verbose_name = 'Annual operating budget')
  budget3 = models.FileField(
      upload_to='/', max_length=255, verbose_name = 'Balance sheet')
  project_budget_file = models.FileField(
      upload_to='/', max_length=255, verbose_name = 'Project budget')
  fiscal_letter = models.FileField(upload_to='/', max_length=255)

  extended_deadline = models.DateTimeField(blank=True, null=True,
      help_text = 'Allows this draft to be edited/submitted past the grant cycle close.')
                                           

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
  submission_time = models.DateTimeField(blank=True, default=timezone.now,
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
     'to those communities?</li><li>What is your organization\'s <span '
     'class="has-more-info" id="nar-2">leadership body?</span></li></ul>'), #2
    ('Social Justice Fund prioritizes groups that understand and address the '
    'underlying, or root causes of the issues, and that bring people together '
    'to build collective power.<ul><li>What problems, needs or issues does '
    'your work address?</li><li>What are the root causes of these issues?</li>'
    '<li>How does your organization build collective power?</li><li>How will '
    'your work change the root causes and underlying power dynamics of the '
    'identified problems, needs or issues?</li></ul>'), #3
    ('Please describe your workplan, covering at least the next 12 months. '
     '(You will list the activities and objectives in the timeline form below,)'
     '<ul><li>What are your overall <span class="has-more-info" id="nar-4">'
     'goals, objectives and strategies</span> for the coming year?</li>'
     '<li>How will you assess whether you have met your goals and objectives?'
     '</li></ul>'), #4
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
     'white anti-racist allies critical to achieving racial justice.</i>'
     'If your organization\'s <span class="has-more-info" id="nar-6">'
     'leadership body</span> is majority white, also describe how you work as '
     'an ally to communities of color. Be as specific as possible, and list at '
     'least one organization led by people of color that we can contact as a '
     'reference for your racial justice work. Include their name, '
     'organization, phone number and email.') #6
  ]
  HELP_TEXTS = {
    'leadership': ('Your organization\'s leadership body is the group of '
        'people who together make strategic decisions about the '
        'organization\'s direction, provide oversight and guidance, and are '
        'ultimately responsible for the organization\'s mission and ability '
        'to carry out its mission. In most cases, this will be a Board of '
        'Directors, but it might also be a steering committee, collective, '
        'or other leadership structure.'),
    'goals': ('<ul><li>A goal is what your organization wants to achieve or '
        'accomplish. You may have both internal goals (how this work will '
        'impact your organization) and external goals (how this work will '
        'impact your broader community).</li><li>An objective is generally '
        'narrower and more specific than a goal, like a stepping stone along '
        'the way.</li><li>A strategy is a road map for achieving your goal. '
        'How will you get there? A strategy will generally encompass '
        'multiple activities or tactics.</li></ul>'),
  }

  narrative1 = models.TextField(validators=[WordLimitValidator(NARRATIVE_CHAR_LIMITS[1])],
                                verbose_name = NARRATIVE_TEXTS[1])
  narrative2 = models.TextField(validators=[WordLimitValidator(NARRATIVE_CHAR_LIMITS[2])],
                                verbose_name = NARRATIVE_TEXTS[2],
                                help_text=HELP_TEXTS['leadership'])
  narrative3 = models.TextField(validators=[WordLimitValidator(NARRATIVE_CHAR_LIMITS[3])],
                                verbose_name = NARRATIVE_TEXTS[3])
  narrative4 = models.TextField(validators=[WordLimitValidator(NARRATIVE_CHAR_LIMITS[4])],
                                verbose_name = NARRATIVE_TEXTS[4],
                                help_text = HELP_TEXTS['goals'])
  narrative5 = models.TextField(validators=[WordLimitValidator(NARRATIVE_CHAR_LIMITS[5])],
                                verbose_name = NARRATIVE_TEXTS[5])
  narrative6 = models.TextField(validators=[WordLimitValidator(NARRATIVE_CHAR_LIMITS[6])],
                                verbose_name = NARRATIVE_TEXTS[6],
                                help_text = HELP_TEXTS['leadership'])
  cycle_question = models.TextField(validators=[WordLimitValidator(NARRATIVE_CHAR_LIMITS[7])],
                                    blank=True)

  timeline = models.TextField(
      verbose_name='Please fill in this timeline to describe your activities '
                   'over the next five quarters. This will not exactly match '
                   'up with the time period funded by this grant. We are '
                   'asking for this information to give us an idea of what your '
                   'work looks like: what you are doing and how those '
                   'activities intersect and build on each other and move you '
                   'towards your goals. Because our grants are usually general '
                   'operating funds, we want to get a sense of what your '
                   'organizing work looks like over time. Note: We understand '
                   'that this timeline is based only on what you know right '
                   'now and that circumstances change. If you receive this '
                   'grant, you will submit a brief report one year later, which '
                   'will ask you what progress you\'ve made on the goals '
                   'outlined in this application or, if you changed direction, '
                   'why.')

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
  racial_justice_ref1_name = models.CharField(verbose_name='Name', max_length=150, blank=True)
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
  budget = models.FileField( #no longer in use
      upload_to='/', max_length=255, validators=[validate_file_extension], blank=True)
  demographics = models.FileField(
      verbose_name = 'Diversity chart', upload_to='/', max_length=255,
      validators=[validate_file_extension])
  funding_sources = models.FileField(
      upload_to='/', max_length=255, validators=[validate_file_extension])
  budget1 = models.FileField(
      verbose_name = 'Annual statement', upload_to='/', max_length=255,
      validators=[validate_file_extension],
      help_text = ('This is the statement of actual income and expenses for '
                   'the most recent completed fiscal year. Upload in your own '
                   'format, but do not send your annual report, tax returns, '
                   'or entire audited financial statement.'))
  budget2 = models.FileField(
      verbose_name = 'Annual operating budget', upload_to='/', max_length=255,
      validators=[validate_file_extension],
      help_text = ('This is a projection of all known and estimated income and '
                   'expenses for the current fiscal year. You may upload in '
                   'your own format or use our budget form. NOTE: If your '
                   'fiscal year will end within three months of this grant '
                   'application deadline, please also attach your operating '
                   'budget for the next fiscal year, so that we can get a more '
                   'accurate sense of your organization\'s situation.'))
  budget3 = models.FileField(
      verbose_name = 'Balance sheet', upload_to='/', max_length=255,
      validators=[validate_file_extension],
      help_text = ('This is a snapshot of your financial status at the moment: '
                   'a brief, current statement of your assets, liabilities, '
                   'and cash on hand. Upload in your own format.'))
  project_budget_file = models.FileField(
      verbose_name = 'Project budget (if applicable)', upload_to='/',
      max_length=255, validators=[validate_file_extension], blank=True,
      help_text = ('This is required only if you are requesting '
                   'project-specific funds. Otherwise, it is optional. You '
                   'may upload in your own format or use our budget form.'))
  fiscal_letter = models.FileField(
      upload_to='/', blank=True, verbose_name = 'Fiscal sponsor letter',
      help_text=('Letter from the sponsor stating that it agrees to act as your '
                 'fiscal sponsor and supports Social Justice Fund\'s mission.'),
      max_length=255, validators=[validate_file_extension])

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
    return '%s - %s' % (unicode(self.organization), unicode(self.grant_cycle))

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

  """
  def clean(self):
    Make sure pre-screening status is valid
    app = self.application
    if app and app.pre_screening_status < 50:
        raise ValidationError('An application be pre-screened in before it can '
                              'be assigned to a giving project. Please correct '
                              'the pre-screening status and try again.')
  """

  class Meta:
    unique_together = ('giving_project', 'application')

  def __unicode__(self):
    return '%s - %s' % (self.giving_project.title, self.application)


class GrantApplicationLog(models.Model):
  date = models.DateTimeField(default = timezone.now)
  organization = models.ForeignKey(Organization)
  application = models.ForeignKey(GrantApplication, null=True, blank=True, help_text = 'Optional - if this log entry relates to a specific grant application, select it from the list')
  staff = models.ForeignKey(User)
  contacted = models.CharField(max_length=255, help_text = 'Person from the organization that you talked to, if applicable.', blank=True)
  notes = models.TextField()

  class Meta:
    ordering = ['-date']

class GivingProjectGrant(models.Model):
  created = models.DateTimeField(default=timezone.now)

  project_app = models.OneToOneField(ProjectApp)

  amount = models.DecimalField(max_digits=8, decimal_places=2)
  check_number = models.PositiveIntegerField(null=True, blank=True)
  check_mailed = models.DateField(null=True, blank=True)

  agreement_mailed = models.DateField(null=True, blank=True)
  agreement_returned = models.DateField(null=True, blank=True)
  approved = models.DateField(verbose_name='Date approved by the ED', null=True, blank=True)

  class Meta:
    ordering = ['-created']

  def agreement_due(self):
    if self.agreement_mailed:
      return self.agreement_mailed + timedelta(days=30)
    else:
      return None

  def yearend_due(self):
    if self.agreement_returned:
      return self.agreement_returned.replace(year = self.agreement_returned.year + 1)
    else:
      return None


class SponsoredProgramGrant(models.Model):

  entered = models.DateTimeField(default=timezone.now)
  organization = models.ForeignKey(Organization)
  amount = models.PositiveIntegerField()
  check_number = models.PositiveIntegerField(null=True, blank=True)
  check_mailed = models.DateField(null=True, blank=True)
  approved = models.DateField(verbose_name='Date approved by the ED',
                              null=True, blank=True)

  description = models.TextField(blank=True)

  class Meta:
    ordering = ['organization']


class YearEndReport(models.Model):

  award = models.ForeignKey(GivingProjectGrant, unique=True)
  submitted = models.DateTimeField(default=timezone.now())
  contact_person = models.TextField() # Name, title
  email = models.EmailField(max_length=255)
  phone = models.CharField(max_length=20)
  website = models.CharField(max_length=255) #autofill based on app

  summarize_last_year = models.TextField(
      verbose_name=
        ('1. Thinking about the Giving Project volunteers who decided to fund '
        'you last year, including those you met on your site visit, what would '
        'you like to tell them about what you’ve done over the last year?'))
  goal_progress = models.TextField(blank=True, verbose_name=
        ('2. Please refer back to your application from last year. Looking at '
         'the goals you outlined in your application, what progress have you '
         'made on each? If you were unable to achieve those goals or changed '
         'your direction, please explain why.'))
  quantitative_measures = models.TextField(verbose_name=
      ('3. Do you evaluate your work by any quantitative measures (e.g., number '
        'of voters registered, members trained, leaders developed, etc.)? If '
        'so, provide that information:')) 
  evaluation = models.TextField(verbose_name=
      ('4. What other type of evaluations do you use internally? Please share '
       'any outcomes that are relevant to the work funded by this grant.'))
  achieved = models.TextField(verbose_name=
      ('5. What specific victories, benchmarks, and/or policy changes (local, '
       'state, regional, or national) have you achieved over the past year?'))
  collboration = models.TextField(verbose_name=
      ('6. What other organizations did you work with to achieve those '
       'accomplishments?'))
  new_funding = models.TextField(verbose_name=
      ('7. Did your grant from Social Justice Fund help you access any new '
       'sources of funding? If so, please explain.'))
  major_changes = models.TextField(verbose_name=
      ('8. Describe any major staff or board changes or other major '
        'organizational changes in the past year.'))
  total_size = models.PositiveIntegerField(verbose_name=
      ('9. What is the total size of your base? That is, how many people, '
        'including paid staff, identify as part of your organization?'))
  donations_count = models.PositiveIntegerField(verbose_name=
      ('10. How many individuals gave a financial contribution of any size to '
        'your organization in the last year? How many individuals made a '
        'financial contribution the previous year?'))

  stay_informed = models.TextField(verbose_name=
      ('11. What is the best way for us to stay informed about your work? '
       '(Enter any/all that apply)'))

  other_comments = models.TextField(blank=True, verbose_name=
      ('12. Other comments or information? Do you have any suggestions for how '
        'SJF can improve its grantmaking programs?')) #json dict - see modelforms


  photo1 = models.FileField(upload_to='/')
  photo2 = models.FileField(upload_to='/')
  photo3 = models.FileField(upload_to='/', help_text='(optional)', blank=True)
  photo4 = models.FileField(upload_to='/', help_text='(optional)', blank=True)

  photo_release = models.FileField(upload_to='/')


class YERDraft(models.Model):

  award = models.ForeignKey(GivingProjectGrant, unique=True)
  modified = models.DateTimeField(default=timezone.now())
  contents = models.TextField(default='{}')

  photo1 = models.FileField(upload_to='/', blank=True)
  photo2 = models.FileField(upload_to='/', blank=True)
  photo3 = models.FileField(upload_to='/', blank=True)
  photo4 = models.FileField(upload_to='/', blank=True)

  photo_release = models.FileField(upload_to='/')

