from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db import models
from django.forms import ModelForm, Textarea
from django.utils import timezone
from google.appengine.ext import blobstore
from sjfnw.fund.models import GivingProject
from sjfnw.utils import IntegerCommaField
import datetime, logging


class Organization(models.Model):
  #registration fields
  name = models.CharField(max_length=255)
  email = models.EmailField() #= django username
  
  #org contact info
  address = models.CharField(max_length=100, null=True)
  city = models.CharField(max_length=50, null=True)
  STATE_CHOICES = (
    ('OR', 'OR'),
    ('WA', 'WA'),
    ('ID', 'ID'),
    ('WY', 'WY'),
    ('MT', 'MT'),
  )
  state = models.CharField(max_length=2,choices=STATE_CHOICES, null=True)
  zip = models.CharField(max_length=50, null=True)
  telephone_number = models.CharField(max_length=20, null=True)
  fax_number = models.CharField(max_length=20, null=True, blank=True)
  email_address = models.EmailField(null=True)
  website = models.CharField(max_length=50, null=True, blank=True)
  
  #org info
  STATUS_CHOICES = (
    ('Tribal government', 'Federally recognized American Indian tribal government'),   
    ('501c3', '501(c)3 organization as recognized by the IRS'),
    ('501c4', '501(c)4 organization as recognized by the IRS'),
    ('Sponsored', 'Sponsored by a 501(c)3, 501(c)4, or federally recognized tribal government'),
  )
  status = models.CharField(max_length=50, choices=STATUS_CHOICES, null=True)
  ein = models.CharField(max_length=50, verbose_name="Organization's or Fiscal Sponsor Organization's EIN", null=True)
  founded = models.PositiveIntegerField(verbose_name='Year organization founded', null=True)
  mission = models.TextField(null=True, blank=True)
  
  #fiscal sponsor info (if applicable)
  fiscal_org = models.CharField(verbose_name='Organization name', max_length=255, null=True, blank=True)
  fiscal_person = models.CharField(verbose_name='Contact person', max_length=255, null=True, blank=True)
  fiscal_telephone = models.CharField(verbose_name='Telephone', max_length=25, null=True, blank=True)
  fiscal_email = models.CharField(verbose_name='Email address', max_length=70, null=True, blank=True)
  fiscal_address = models.CharField(verbose_name='Address/City/State/ZIP', max_length=255, null=True, blank=True)
  fiscal_letter = models.FileField(upload_to='/%Y/', null=True,blank=True)
   
  def __unicode__(self):
    return self.name

class OrgProfile(ModelForm):
  class Meta:
    model = Organization
    exclude = ('name', 'email')

class GrantCycle(models.Model):
  title = models.CharField(max_length=100)
  open = models.DateTimeField()
  close = models.DateTimeField()
  extra_question = models.TextField(blank=True)
  info_page = models.URLField(blank=True)
  email_signature = models.TextField(blank=True)
  
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
  modified = models.DateTimeField(auto_now=True)
  
  contents = models.TextField()
  
  budget = models.FileField(upload_to='draft/', max_length=255)
  demographics = models.FileField(upload_to='draft/', max_length=255)
  funding_sources = models.FileField(upload_to='draft/', max_length=255)
  fiscal_letter = models.FileField(upload_to='draft/', max_length=255)
  
  extended_deadline = models.DateTimeField(help_text = 'Allows this draft to be edited/submitted past the grant cycle close.', blank=True, null=True)

  def __unicode__(self):
    return u'DRAFT - ' + self.organization.name + u' - ' + self.grant_cycle.title
  
  def overdue(self):
    return self.grant_cycle.close >= timezone.now()

  def editable(self):
    deadline = self.grant_cycle.close
    now = timezone.now()
    if deadline > now or (self.extended_deadline and self.extended_deadline > now):
      return True
    else:
      return False
  
  """ only deletes blobinfo, not file itself :(
  def save(self, *args, **kwargs):
    delete = []
    try:
      previous = DraftGrantApplication.objects.get(id=self.id)
      if previous.budget and previous.budget != self.budget:
        delete.append(previous.budget)
      if previous.demographics and previous.demographics != self.demographics:
        delete.append(previous.demographics)
      if previous.fiscal_letter and previous.fiscal_letter != self.fiscal_letter:
        delete.append(previous.fiscal_letter)
      if previous.funding_sources and previous.funding_sources != self.funding_sources:
        delete.append(previous.funding_sources)
    except: pass
    logging.info('Queued for deletion: ' + str(delete))
    count = 0
    for field in delete:
      key = str(field).split('/', 1)[0]
      if key:
        binfo = blobstore.BlobInfo.get(key)
        binfo.delete()
        count += 1
    logging.info('Draft being updated. ' + str(count) + ' old files deleted.')
    super(DraftGrantApplication, self).save(*args, **kwargs)
  """

class CharLimitValidator(MaxLengthValidator):
  message = 'Please limit this response to %(limit_value)s characters or less.'

NARRATIVE_CHAR_LIMITS = [0, 1800, 900, 2700, 1800, 1800, 2700, 1800]
NARRATIVE_TEXTS = ['Placeholder for 0',
  'Describe your organization\'s mission, history and major accomplishments.', #1
  'Social Justice Fund prioritizes groups that are led by the people most impacted by the issues the group is working on, and continually build leadership from within their own communities.<ul><li>Who are the communities most directly impacted by the issues your organization addresses?</li><li>How are those communities involved in the leadership of your organization, and how does your organization remain accountable to those communities?</li></ul>', #2
  'Social Justice Fund prioritizes groups that understand and address the underlying, or root causes of the issues, and that bring people together to build collective power.<ul><li>What problems, needs or issues does your work address?</li><li>What are the root causes of these issues</li><li>How does your organization build collective power?</li><li>How will your work change the root causes and underlying power dynamics of the identified problems, needs or issues?</li></ul>', #3
  'Please describe your workplan, covering at least the next 12 months. (You will list the activities and objectives in the timeline form below the narrative.)<ul><li>What are your overall goals and strategies for the coming year?</li><li>How will you assess whether you have met your objectives and goals?</li></ul>', #4
  'Social Justice Fund prioritizes groups that see themselves as part of a larger movement for social change, and work towards strengthening that movement.<ul><li>Describe at least two coalitions, collaborations, partnerships or networks that you participate in as an approach to social change.</li><li>What are the purposes and impacts of these collaborations?</li><li>What is your organizations role in these collaborations?</li><li>If your collaborations cross issue or constituency lines, how will this will help build a broad, unified, and effective progressive movement?</li></ul>', #5
  'Social Justice Fund prioritizes groups working on racial justice, especially those making connections between racism, economic injustice, homophobia, and other forms of oppression. <i>While we believe people of color must lead the struggle for racial justice, we also realize that the demographics of our region make the work of white anti-racist allies critical to achieving racial justice.</i><ul>  <li>Summarize your organization\'s analysis of inequality and oppression.</li><li>How does your organization live out that analysis internally?</li><li>How does your organization\'s work impact those systems of oppression in the larger society?</li></ul>', #6
  ]

def validate_file_extension(value):
  if not str(value).lower().split(".")[-1] in settings.ALLOWED_FILE_TYPES:
    raise ValidationError(u'That file type is not supported.')

class GrantApplication(models.Model):
  """ Submitted grant application """
  
  #automated fields
  submission_time = models.DateTimeField(auto_now_add=True, verbose_name='Submitted')
  organization = models.ForeignKey(Organization)
  grant_cycle = models.ForeignKey(GrantCycle)
  
  #contact info
  address = models.CharField(max_length=100)
  city = models.CharField(max_length=50)
  STATE_CHOICES = (
    ('OR', 'OR'),
    ('WA', 'WA'),
    ('ID', 'ID'),
    ('WY', 'WY'),
    ('MT', 'MT'),
  )
  state = models.CharField(max_length=2,choices=STATE_CHOICES)
  zip = models.CharField(max_length=50)
  telephone_number = models.CharField(max_length=20)
  fax_number = models.CharField(max_length=20, null=True, blank=True, verbose_name = 'Fax number (optional)')
  email_address = models.EmailField()
  website = models.CharField(max_length=50, null=True, blank=True, verbose_name = 'Website (optional)')
  
  #org info
  STATUS_CHOICES = (
    ('Tribal government', 'Federally recognized American Indian tribal government'),   
    ('501c3', '501(c)3 organization as recognized by the IRS'),
    ('501c4', '501(c)4 organization as recognized by the IRS'),
    ('Sponsored', 'Sponsored by a 501(c)3, 501(c)4, or federally recognized tribal government'),
  )
  status = models.CharField(max_length=50, choices=STATUS_CHOICES)
  ein = models.CharField(max_length=50, verbose_name="Organization or Fiscal Sponsor EIN")
  founded = models.PositiveIntegerField(verbose_name='Year founded')
  mission = models.TextField(verbose_name="Mission statement")
  previous_grants = models.CharField(max_length=255, verbose_name="Previous SJF grants awarded (amounts and year)", blank=True)
  
  #budget info
  start_year = models.CharField(max_length=250,verbose_name='Start date of fiscal year')
  budget_last = models.PositiveIntegerField(verbose_name='Org. budget last fiscal year')
  budget_current = models.PositiveIntegerField(verbose_name='Org. budget this fiscal year')
  
  #this grant info
  grant_request = models.TextField(verbose_name="Briefly summarize the grant request")
  contact_person = models.CharField(max_length=250, verbose_name= 'Name', help_text='Contact person for this grant application')
  contact_person_title = models.CharField(max_length=100, verbose_name='Title')
  grant_period = models.CharField(max_length=250, blank=True, verbose_name='Grant period (if different than fiscal year)')
  amount_requested = models.PositiveIntegerField(verbose_name='Amount requested $')
  SUPPORT_CHOICES = (
    ('General support', 'General support'),   
    ('Project support', 'Project support'),
  )
  support_type = models.CharField(max_length=50, choices=SUPPORT_CHOICES)
  project_title = models.CharField(max_length=250,verbose_name='Project title (if applicable)', null=True, blank=True)
  project_budget = models.PositiveIntegerField(verbose_name='Project budget (if applicable)', null=True, blank=True)
  
  
  #fiscal sponsor
  fiscal_org = models.CharField(verbose_name='Fiscal org. name', max_length=255, null=True, blank=True)
  fiscal_person = models.CharField(verbose_name='Contact person', max_length=255, null=True, blank=True)
  fiscal_telephone = models.CharField(verbose_name='Telephone', max_length=25, null=True, blank=True)
  fiscal_email = models.CharField(verbose_name='Email address', max_length=70, null=True, blank=True)
  fiscal_address = models.CharField(verbose_name='Address/City/State/ZIP', max_length=255, null=True, blank=True)
  fiscal_letter = models.FileField(upload_to='%Y/', null=True,blank=True, verbose_name = 'Fiscal sponsor letter', help_text='Letter from the sponsor stating that it agrees to act as your fiscal sponsor and supports Social Justice Fund\'s mission.', validators=[validate_file_extension], max_length=255)
  
  #narrative
  narrative1 = models.TextField(validators=[CharLimitValidator(NARRATIVE_CHAR_LIMITS[1])], verbose_name = NARRATIVE_TEXTS[1])
  narrative2 = models.TextField(validators=[CharLimitValidator(NARRATIVE_CHAR_LIMITS[2])], verbose_name = NARRATIVE_TEXTS[2])
  narrative3 = models.TextField(validators=[CharLimitValidator(NARRATIVE_CHAR_LIMITS[3])], verbose_name = NARRATIVE_TEXTS[3])
  narrative4 = models.TextField(validators=[CharLimitValidator(NARRATIVE_CHAR_LIMITS[4])], verbose_name = NARRATIVE_TEXTS[4])
  narrative5 = models.TextField(validators=[CharLimitValidator(NARRATIVE_CHAR_LIMITS[5])], verbose_name = NARRATIVE_TEXTS[5])
  narrative6 = models.TextField(validators=[CharLimitValidator(NARRATIVE_CHAR_LIMITS[6])], verbose_name = NARRATIVE_TEXTS[6])
  cycle_question = models.TextField(validators=[CharLimitValidator(NARRATIVE_CHAR_LIMITS[7])], blank=True)
  
  #references
  collab_ref1_name = models.CharField(help_text='Provide names and contact information for two people who are familiar with your organization\'s role in these collaborations so we can contact them for more information.', verbose_name='Name', max_length = 150)
  collab_ref1_org = models.CharField(verbose_name='Organization', max_length = 150)
  collab_ref1_phone = models.CharField(verbose_name='Phone number',  max_length = 20, blank=True)
  collab_ref1_email = models.EmailField(verbose_name='Email', blank=True)
  
  collab_ref2_name = models.CharField(verbose_name='Name', max_length = 150)
  collab_ref2_org = models.CharField(verbose_name='Organization', max_length = 150)
  collab_ref2_phone = models.CharField(verbose_name='Phone number',  max_length = 20, blank=True)
  collab_ref2_email = models.EmailField(verbose_name='Email', blank=True)
  
  racial_justice_ref1_name = models.CharField(help_text='If you are a primarily white-led organization, also describe how you work as an ally to communities of color. Be as specific as possible, and list at least one organization led by people of color that we can contact as a reference for your racial justice work.', verbose_name='Name', max_length = 150, blank=True)
  racial_justice_ref1_org = models.CharField(verbose_name='Organization', max_length = 150, blank=True)
  racial_justice_ref1_phone = models.CharField(verbose_name='Phone number', max_length = 20, blank=True)
  racial_justice_ref1_email = models.EmailField(verbose_name='Email', blank=True)
 
  racial_justice_ref2_name = models.CharField(verbose_name='Name', max_length = 150, blank=True)
  racial_justice_ref2_org = models.CharField(verbose_name='Organization', max_length = 150, blank=True)
  racial_justice_ref2_phone = models.CharField(verbose_name='Phone number',  max_length = 20, blank=True)
  racial_justice_ref2_email = models.EmailField(verbose_name='Email', blank=True) 
  
  #files
  budget = models.FileField(upload_to='%Y/', max_length=255)
  demographics = models.FileField(upload_to='%Y/', max_length=255)
  funding_sources = models.FileField(upload_to='%Y/', max_length=255)
  #timeline?
  
  #admin fields  
  SCREENING_CHOICES = (
    (10, 'Received'),
    (20, 'Incomplete'),
    (30, 'Complete'),
    (40, 'Proposal Denied'),
    (50, 'Proposal Accepted'), #cutoff for gp view
    (60, 'Grant Denied'),  
    (70, 'Grant Issued'),
    (80, 'Grant Paid'),
    (90, 'Closed'),
  )
  screening_status = models.IntegerField(choices=SCREENING_CHOICES, default=10)
  giving_project = models.ForeignKey(GivingProject, null=True, blank=True)
  scoring_bonus_poc = models.BooleanField(default=False, verbose_name='Scoring bonus for POC-led?')
  scoring_bonus_geo = models.BooleanField(default=False, verbose_name='Scoring bonus for geographic diversity?')
  
  def __unicode__(self):
    return unicode(self.organization)
  
  def view_link(self):
    return '<a href="/grants/view/' + str(self.pk) + '" target="_blank">View application</a>'
  view_link.allow_tags = True

def addCssLabel(label_text):
  return u'<span class="label">' + (label_text or '') + u'</span>'

def custom_integer_field(f, **kwargs):
  if isinstance(f, models.PositiveIntegerField) and f.verbose_name != 'Year founded':
    label = f.verbose_name
    required = not f.blank
    return IntegerCommaField(label = label, required = required)
  else:
    return f.formfield()

class GrantApplicationForm(ModelForm):
  formfield_callback = custom_integer_field
  class Meta:
    model = GrantApplication
    widgets = {
          'mission': Textarea(attrs={'rows': 3, 'onKeyUp':'charLimitDisplay(this, 300)'}),
          'grant_request': Textarea(attrs={'rows': 3}),
          'narrative1': Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(NARRATIVE_CHAR_LIMITS[1]) + ')'}),
          'narrative2': Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(NARRATIVE_CHAR_LIMITS[2]) + ')'}),
          'narrative3': Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(NARRATIVE_CHAR_LIMITS[3]) + ')'}),
          'narrative4': Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(NARRATIVE_CHAR_LIMITS[4]) + ')'}),
          'narrative5': Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(NARRATIVE_CHAR_LIMITS[5]) + ')'}),
          'narrative6': Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(NARRATIVE_CHAR_LIMITS[6]) + ')'}),
        }
  
  def __init__(self, *args, **kwargs):
    super(GrantApplicationForm, self).__init__(*args, **kwargs)
    for key in self.fields:
      if self.fields[key].required:
        self.fields[key].widget.attrs['class'] = 'required'
      self.fields[key].label = addCssLabel(self.fields[key].label)
  
  def clean(self):
    cleaned_data = super(GrantApplicationForm, self).clean()
    
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
    
    #require cycle question if given
    cycle = cleaned_data.get('grant_cycle')
    answer = cleaned_data.get('cycle_question')
    logging.info(cycle.extra_question)
    logging.info(answer)
    if cycle.extra_question and not answer:
      self._errors["cycle_question"] = '<div class="form_error">This field is required.</div>'
      
    return cleaned_data

"""
class SJFSettings(models.Model):
  name = models.CharField(max_length=100, default="SJF Settings", unique=True)
  
  support_email = models.EmailField(help_text = 'Address displayed on the site for technical support.')
  fund_from_email = models.EmailField(help_text = 'Address from which fundraising app emails are sent.')
  grant_from_email = models.EmailField(help_text = 'Address from which grant app emails are sent.')
  
  narrative_heading = models.TextField(help_text = 'Paragraph displayed at the start of the narratives section.', default = 'Be as specific as possible when responding to each item. Your responses will reflect on the soundness of your organizational structure, your social change strategy and your organizing plan. Please keep in mind that the strength of your written application will significantly influence the overall score you receive in the decision-making process.')
  narrative1 = models.TextField()
  narrative2 = models.TextField()
  narrative3 = models.TextField()
  narrative4 = models.TextField()
  narrative5 = models.TextField()
  narrative6 = models.TextField()
  narrative7 = models.TextField()
  """
