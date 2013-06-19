from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import BaseValidator
from django.db import models
from django.forms import ModelForm, Textarea
from django.forms.widgets import FileInput, MultiWidget
from django.utils import timezone
from django.utils.text import capfirst
from sjfnw.fund.models import GivingProject
from sjfnw.forms import IntegerCommaField, PhoneNumberField
import logging, json, re
from sjfnw import constants
from datetime import timedelta

class TimelineWidget(MultiWidget):
  def __init__(self, attrs=None):
    _widgets = (
      Textarea(attrs={'rows':'5', 'cols':'20'}),
      Textarea(attrs={'rows':'5'}),
      Textarea(attrs={'rows':'5'}),
      Textarea(attrs={'rows':'5', 'cols':'20'}),
      Textarea(attrs={'rows':'5'}),
      Textarea(attrs={'rows':'5'}),
      Textarea(attrs={'rows':'5', 'cols':'20'}),
      Textarea(attrs={'rows':'5'}),
      Textarea(attrs={'rows':'5'}),
      Textarea(attrs={'rows':'5', 'cols':'20'}),
      Textarea(attrs={'rows':'5'}),
      Textarea(attrs={'rows':'5'}),
      Textarea(attrs={'rows':'5', 'cols':'20'}),
      Textarea(attrs={'rows':'5'}),
      Textarea(attrs={'rows':'5'}),
    )
    super(TimelineWidget, self).__init__(_widgets, attrs)


  def decompress(self, value):
    """ break single database value up for widget display
          argument: database value (json string representing list of vals)
          returns: list of values to be displayed in widgets """

    if value:
      return json.loads(value)
    return [None, None, None, None, None, None, None, None, None, None, None,
            None, None, None, None]


  def format_output(self, rendered_widgets):
    """
    format the widgets for display
      args: list of rendered widgets
      returns: a string of HTML for displaying the widgets
    """

    html = ('<table id="timeline_form"><tr class="heading"><td></td>'
            '<th>date range</th><th>activities</th>'
            '<th>goals/objectives</th></tr>')
    for i in range(0, len(rendered_widgets), 3):
      html += ('<tr><th class="left">q' + str((i+3)/3) + '</th><td>' +
              rendered_widgets[i] + '</td><td>' + rendered_widgets[i+1] +
              '</td><td>' + rendered_widgets[i+2] +'</td></tr>')
    html += '</table>'
    return html

  def value_from_datadict(self, data, files, name):
    """ Consolodate widget data into a single value
        returns:
          json'd list of values """

    val_list = []
    for i, widget in enumerate(self.widgets):
      val_list.append(widget.value_from_datadict(data, files, name +
                                                  '_%s' % i))
    return json.dumps(val_list)

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

class Organization(models.Model):
  #registration fields
  name = models.CharField(max_length=255)
  email = models.EmailField(max_length=100, verbose_name='Email(login)',
                            unique=True) #= django username

  #org contact info
  address = models.CharField(max_length=100, blank=True)
  city = models.CharField(max_length=50, blank=True)
  state = models.CharField(max_length=2, choices=STATE_CHOICES, null=True,
                           blank=True)
  zip = models.CharField(max_length=50, blank=True)
  telephone_number = models.CharField(max_length=20, blank=True)
  fax_number = models.CharField(max_length=20, blank=True)
  email_address = models.EmailField(max_length=100, blank=True)
  website = models.CharField(max_length=50, null=True, blank=True)

  #org info
  status = models.CharField(max_length=50, choices=STATUS_CHOICES, null=True,
                            blank=True)
  ein = models.CharField(max_length=50,
                         verbose_name="Organization's or Fiscal Sponsor Organization's EIN",
                         blank=True)
  founded = models.PositiveIntegerField(verbose_name='Year founded',
                                        null=True, blank=True)
  mission = models.TextField(blank=True)

  #fiscal sponsor info (if applicable)
  fiscal_org = models.CharField(verbose_name='Organization name',
                                max_length=255, null=True, blank=True)
  fiscal_person = models.CharField(verbose_name='Contact person',
                                   max_length=255, null=True, blank=True)
  fiscal_telephone = models.CharField(verbose_name='Telephone',
                                      max_length=25, null=True, blank=True)
  fiscal_email = models.CharField(verbose_name='Email address',
                                  max_length=100, null=True, blank=True)
  fiscal_address = models.CharField(verbose_name='Address',
                                    max_length=255, null=True, blank=True)
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

class OrgProfile(ModelForm):
  class Meta:
    model = Organization
    exclude = ('name', 'email')

class GrantCycle(models.Model):
  title = models.CharField(max_length=100)
  open = models.DateTimeField()
  close = models.DateTimeField()
  extra_question = models.TextField(blank=True)
  info_page = models.URLField()
  email_signature = models.TextField(blank=True)
  conflicts = models.TextField(blank=True,
                               help_text='Track any conflicts of interest '
                               '(automatic & personally declared) that occurred'
                               ' during this cycle.')

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
    now = timezone.now()
    if deadline > now or (self.extended_deadline and
                          self.extended_deadline > now):
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
  previous_grants = models.CharField(max_length=255,
                                     verbose_name=("Previous SJF grants awarded"
                                                  " (amounts and year)"),
                                     blank=True)

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
  project_title = models.CharField(max_length=250, null=True, blank=True,
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
  NARRATIVE_CHAR_LIMITS = [0, 300, 150, 450, 300, 300, 450, 300]
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

  SCREENING_CHOICES = (
    (10, 'Received'),
    (20, 'Incomplete'),
    (30, 'Complete'),
    (40, 'Pre-screened out'),
    (45, 'Screened out by sub-committee'),
    (50, 'Pre-screened in'), #readable, scorable
    (60, 'Screened out'),
    (70, 'Site visit awarded'), #site visit reports
    (80, 'Grant denied'),
    (90, 'Grant issued'),
    (100, 'Grant paid'),
    (110, 'Year-end report overdue'),
    (120, 'Year-end report received'),
    (130, 'Closed'),)
  #admin fields
  screening_status = models.IntegerField(choices=SCREENING_CHOICES, default=10)
  giving_project = models.ForeignKey(GivingProject, null=True, blank=True)
  scoring_bonus_poc = models.BooleanField(default=False, verbose_name='Scoring bonus for POC-led')
  scoring_bonus_geo = models.BooleanField(default=False, verbose_name='Scoring bonus for geographic diversity')

  class Meta:
    unique_together = ('organization', 'grant_cycle')

  def __unicode__(self):
    return unicode(self.organization) + u' - ' + unicode(self.grant_cycle) + u' - ' + unicode(self.submission_time.year)

  def id_number(self):
    return self.pk + 5211 #picking up after the access db

  def view_link(self):
    return '<a href="/grants/view/' + str(self.pk) + '" target="_blank">View application</a>'
  view_link.allow_tags = True

  def timeline_display(self):
    logging.info(type(self.timeline))
    timeline = json.loads(self.timeline)
    html = '<table id="timeline_display"><tr class="heading"><td></td><th>date range</th><th>activities</th><th>goals/objectives</th></tr>'
    for i in range(0, 15, 3):
      html += '<tr><th class="left">q' + str((i+3)/3) + '</th><td>' + timeline[i] + '</td><td>' + timeline[i+1] + '</td><td>' + timeline[i+2] +'</td></tr>'
    html += '</table>'
    return html
  timeline_display.allow_tags = True

  @classmethod
  def fiscal_fields(cls):
    return [f for f in cls._meta.get_all_field_names() if f.startswith('fiscal')]

  @classmethod
  def file_fields(cls):
    return [f.name for f in cls._meta.fields if isinstance(f, models.FileField)]

def custom_fields(f, **kwargs): #sets phonenumber and money fields
  money_fields = ['budget_last', 'budget_current', 'amount_requested', 'project_budget']
  phone_fields = ['telephone_number', 'fax_number', 'fiscal_telephone',
                  'collab_ref1_phone', 'collab_ref2_phone',
                  'racial_justice_ref1_phone', 'racial_justice_ref2_phone']
  kwargs['required'] = not f.blank
  if f.verbose_name:
    kwargs['label'] = capfirst(f.verbose_name)
  if f.name in money_fields:
    return IntegerCommaField(**kwargs)
  elif f.name in phone_fields:
    return PhoneNumberField(**kwargs)
  else:
    return f.formfield(**kwargs)

class GrantApplicationModelForm(ModelForm):
  formfield_callback = custom_fields
  class Meta:
    model = GrantApplication
    exclude = ['screening_status', 'submission_time'] #auto fields with defaults
    widgets = {
      #char limits
      'mission': Textarea(attrs={'rows': 3, 'onKeyUp':'charLimitDisplay(this, 150)'}),
      'grant_request': Textarea(attrs={'rows': 3, 'onKeyUp':'charLimitDisplay(this, 100)'}),
      'narrative1': Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(GrantApplication.NARRATIVE_CHAR_LIMITS[1]) + ')'}),
      'narrative2': Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(GrantApplication.NARRATIVE_CHAR_LIMITS[2]) + ')'}),
      'narrative3': Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(GrantApplication.NARRATIVE_CHAR_LIMITS[3]) + ')'}),
      'narrative4': Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(GrantApplication.NARRATIVE_CHAR_LIMITS[4]) + ')'}),
      'narrative5': Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(GrantApplication.NARRATIVE_CHAR_LIMITS[5]) + ')'}),
      'narrative6': Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(GrantApplication.NARRATIVE_CHAR_LIMITS[6]) + ')'}),
      'cycle_question': Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(GrantApplication.NARRATIVE_CHAR_LIMITS[7]) + ')'}),
      #file callbacks
      'budget': FileInput(attrs={'onchange':'fileChanged(this.id);'}),
      'demographics': FileInput(attrs={'onchange':'fileChanged(this.id);'}),
      'funding_sources': FileInput(attrs={'onchange':'fileChanged(this.id);'}),
      'fiscal_letter': FileInput(attrs={'onchange':'fileChanged(this.id);'}),
      'budget1': FileInput(attrs={'onchange':'fileChanged(this.id);'}),
      'budget2': FileInput(attrs={'onchange':'fileChanged(this.id);'}),
      'budget3': FileInput(attrs={'onchange':'fileChanged(this.id);'}),
      'project_budget_file': FileInput(attrs={'onchange':'fileChanged(this.id);'}),
      #timeline
      'timeline':TimelineWidget(),
    }

  def __init__(self, cycle, *args, **kwargs):
    super(GrantApplicationModelForm, self).__init__(*args, **kwargs)
    if cycle and cycle.extra_question:
      self.fields['cycle_question'].required = True
      logging.info('Requiring the cycle question')

  def clean(self):
    cleaned_data = super(GrantApplicationModelForm, self).clean()

    #timeline
    timeline = cleaned_data.get('timeline')
    timeline = json.loads(timeline)
    empty = False
    incomplete = False
    for i in range(0, 13, 3):
      date = timeline[i]
      act = timeline[i+1]
      obj = timeline[i+2]
      if i == 0 and not (date or act or obj):
        empty = True
      if (date or act or obj) and not (date and act and obj):
        incomplete = True
    if incomplete:
      self._errors['timeline'] = '<div class="form_error">All three columns are required for each quarter that you include in your timeline.</div>'
    elif empty:
      self._errors['timeline'] = '<div class="form_error">This field is required.</div>'

    #collab refs - require phone or email
    phone = cleaned_data.get('collab_ref1_phone')
    email = cleaned_data.get('collab_ref1_email')
    if not phone and not email:
      self._errors["collab_ref1_phone"] = '<div class="form_error">Enter a phone number or email.</div>'
    phone = cleaned_data.get('collab_ref2_phone')
    email = cleaned_data.get('collab_ref2_email')
    if not phone and not email:
      self._errors["collab_ref2_phone"] = '<div class="form_error">Enter a phone number or email.</div>'

    #racial justice refs - require full set if any
    name = cleaned_data.get('racial_justice_ref1_name')
    org = cleaned_data.get('racial_justice_ref1_org')
    phone = cleaned_data.get('racial_justice_ref1_phone')
    email = cleaned_data.get('racial_justice_ref1_email')
    if name or org or phone or email:
      if not name:
        self._errors["racial_justice_ref1_name"] = '<div class="form_error">Enter a contact person.</div>'
      if not org:
        self._errors["racial_justice_ref1_org"] = '<div class="form_error">Enter the organization name.</div>'
      if not phone and not email:
        self._errors["racial_justice_ref1_phone"] = '<div class="form_error">Enter a phone number or email.</div>'
    name = cleaned_data.get('racial_justice_ref2_name')
    org = cleaned_data.get('racial_justice_ref2_org')
    phone = cleaned_data.get('racial_justice_ref2_phone')
    email = cleaned_data.get('racial_justice_ref2_email')
    if name or org or phone or email:
      if not name:
        self._errors["racial_justice_ref2_name"] = '<div class="form_error">Enter a contact person.</div>'
      if not org:
        self._errors["racial_justice_ref2_org"] = '<div class="form_error">Enter the organization name.</div>'
      if not phone and not email:
        self._errors["racial_justice_ref2_phone"] = '<div class="form_error">Enter a phone number or email.</div>'

    #project - require title & budget if type
    support_type = cleaned_data.get('support_type')
    if support_type == 'Project support':
      if not cleaned_data.get('project_budget'):
        self._errors["project_budget"] = '<div class="form_error">This field is required when applying for project support.</div>'
      if not cleaned_data.get('project_title'):
        self._errors["project_title"] = '<div class="form_error">This field is required when applying for project support.</div>'

    #budget files - require all-in-one or full set
    budget = cleaned_data.get('budget')
    b1 = cleaned_data.get('budget1')
    b2 = cleaned_data.get('budget2')
    b3 = cleaned_data.get('budget3')
    if not budget:
      if not (b1 or b2): #no budget files entered at all
        self._errors["budget"] = '<div class="form_error">Budget documents are required. You may upload them as one file or as multuple files.</div>'
      else: #some files uploaded
        if not b1:
          self._errors["budget1"] = '<div class="form_error">This field is required.</div>'
        if not b2:
          self._errors["budget2"] = '<div class="form_error">This field is required.</div>'
      #require project budget if applicable and if not all-in-one
      if (support_type == 'Project support') and not cleaned_data.get('project_budget_file'):
        self._errors["project_budget_file"] = '<div class="form_error">This field is required when applying for project support.</div>'
    elif b1 or b2 or b3: #all-in-one included + other file(s)
      self._errors["budget"] = '<div class="form_error">Budget documents should be uploaded all in one file OR in the individual fields below.</div>'

    #fiscal info/file - require all if any
    org = cleaned_data.get('fiscal_org')
    person = cleaned_data.get('fiscal_person')
    phone = cleaned_data.get('fiscal_telephone')
    email = cleaned_data.get('fiscal_email')
    address = cleaned_data.get('fiscal_address')
    city = cleaned_data.get('fiscal_city')
    state = cleaned_data.get('fiscal_state')
    zip = cleaned_data.get('fiscal_zip')
    file = cleaned_data.get('fiscal_letter')
    if (org or person or phone or email or address or city or state or zip):
      if not org:
        self._errors["fiscal_org"] = '<div class="form_error">This field is required.</div>'
      if not person:
        self._errors["fiscal_person"] = '<div class="form_error">This field is required.</div>'
      if not phone:
        self._errors["fiscal_telephone"] = '<div class="form_error">This field is required.</div>'
      if not email:
        self._errors["fiscal_email"] = '<div class="form_error">This field is required.</div>'
      if not address:
        self._errors["fiscal_address"] = '<div class="form_error">This field is required.</div>'
      if not city:
        self._errors["fiscal_city"] = '<div class="form_error">This field is required.</div>'
      if not state:
        self._errors["fiscal_state"] = '<div class="form_error">This field is required.</div>'
      if not zip:
        self._errors["fiscal_zip"] = '<div class="form_error">This field is required.</div>'
      if not file:
        self._errors["fiscal_letter"] = '<div class="form_error">This field is required.</div>'

    return cleaned_data

class GrantApplicationLog(models.Model):
  date = models.DateTimeField(default = timezone.now())
  organization = models.ForeignKey(Organization)
  application = models.ForeignKey(GrantApplication, null=True, blank=True, help_text = 'Optional - if this log entry relates to a specific grant application, select it from the list')
  staff = models.ForeignKey(User)
  contacted = models.CharField(max_length=255, help_text = 'Person from the organization that you talked to, if applicable.', blank=True)
  notes = models.TextField()

class GrantAward(models.Model):
  created = models.DateTimeField(default=timezone.now())

  application = models.ForeignKey(GrantApplication)

  amount = models.DecimalField(max_digits=8, decimal_places=2)
  check_number = models.PositiveIntegerField(null=True, blank=True)
  check_mailed = models.DateField(null=True, blank=True)

  agreement_mailed = models.DateField(null=True, blank=True)
  agreement_returned = models.DateField(null=True, blank=True)
  approved = models.DateField(verbose_name='Date approved by the ED', null=True, blank=True)

  def year(self):
    if self.check_mailed:
      return self.check_mailed.year
    else:
      return None

  def agreement_due(self):
    if self.agreement_mailed:
      return self.agreement_mailed + timedelta(days=30)
    else:
      return None

  def yearend_due(self):
    with self.agreement_mailed as mailed:
      if mailed:
        return (mailed + timedelta(days=30)).replace(year = mailed.year+1)
      else:
        return None

