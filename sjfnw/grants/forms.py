from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.utils import timezone
from django.utils.safestring import mark_safe
import models, datetime, logging
from sjfnw.utils import IntegerCommaField
from sjfnw import constants

class LoginForm(forms.Form):
  email = forms.EmailField()
  password = forms.CharField(widget=forms.PasswordInput())

class RegisterForm(forms.Form):
  email = forms.EmailField(max_length=100)
  password = forms.CharField(widget=forms.PasswordInput())
  passwordtwo = forms.CharField(widget=forms.PasswordInput(), label="Re-enter password")
  organization = forms.CharField()
  
  def clean(self): #make sure passwords match
    cleaned_data = super(RegisterForm, self).clean()
    password = cleaned_data.get("password")
    passwordtwo = cleaned_data.get("passwordtwo")
    if password and passwordtwo and password != passwordtwo:
      self._errors["password"] = self.error_class(["Passwords did not match."])
      del cleaned_data["password"]
      del cleaned_data["passwordtwo"]
    return cleaned_data 

class CharLimitValidator(MaxLengthValidator):
  message = 'Please limit this response to %(limit_value)s characters or less.'

def validate_file_extension(value):
  if not str(value).lower().split(".")[-1] in constants.ALLOWED_FILE_TYPES:
    raise ValidationError(u'That file type is not supported.')

class GrantApplicationForm(forms.Form):
  """ Grant application form"""
  
  #contact info
  address = forms.CharField(max_length=100)
  city = forms.CharField(max_length=50)
  state = forms.ChoiceField(choices=models.STATE_CHOICES)
  zip = forms.CharField(max_length=50)
  telephone_number = forms.CharField(max_length=20)
  fax_number = forms.CharField(max_length=20, required=False, label = 'Fax number (optional)')
  email_address = forms.EmailField()
  website = forms.CharField(max_length=50, required=False, label = 'Website (optional)')
  
  #org info
  status = forms.ChoiceField(choices= [('', '--- Select one ---')] + models.STATUS_CHOICES)
  ein = forms.CharField(max_length=50, label="Organization or Fiscal Sponsor EIN")
  founded = IntegerCommaField(label='Year founded')
  mission = forms.CharField(label="Mission statement", validators=[CharLimitValidator(750)], widget=forms.Textarea(attrs={'rows': 3, 'onKeyUp':'charLimitDisplay(this, 750)'}))
  previous_grants = forms.CharField(max_length=255, label="Previous SJF grants awarded (amounts and year)", required=False)
  
  #budget info
  start_year = forms.CharField(max_length=250,label='Start date of fiscal year')
  budget_last = IntegerCommaField(label='Org. budget last fiscal year')
  budget_current = IntegerCommaField(label='Org. budget this fiscal year')
  
  #this grant info
  grant_request = forms.CharField(label="Briefly summarize the grant request", validators=[CharLimitValidator(600)], widget=forms.Textarea(attrs={'rows': 3, 'onKeyUp':'charLimitDisplay(this, 600)'}))
  contact_person = forms.CharField(max_length=250, label= 'Name', help_text='Contact person for this grant application:')
  contact_person_title = forms.CharField(max_length=100, label='Title')
  grant_period = forms.CharField(max_length=250, required=False, label='Grant period (if different than fiscal year)')
  amount_requested = IntegerCommaField(label='Amount requested')
  support_type = forms.ChoiceField(choices=models.SUPPORT_CHOICES)
  project_title = forms.CharField(max_length=250,label='Project title (if applicable)', required=False)
  project_budget = IntegerCommaField(label='Project budget (if applicable)', required=False)
  
  
  #fiscal sponsor
  fiscal_org = forms.CharField(label='Fiscal org. name', max_length=255, required=False)
  fiscal_person = forms.CharField(label='Contact person', max_length=255, required=False)
  fiscal_telephone = forms.CharField(label='Telephone', max_length=25, required=False)
  fiscal_email = forms.CharField(label='Email address', max_length=70, required=False)
  fiscal_address = forms.CharField(label='Address/City/State/ZIP', max_length=255, required=False)
  
  #narratives
  narrative1 = forms.CharField(validators=[CharLimitValidator(models.NARRATIVE_CHAR_LIMITS[1])], label = mark_safe(models.NARRATIVE_TEXTS[1]), widget= forms.Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(models.NARRATIVE_CHAR_LIMITS[1]) + ')'}))
  narrative2 = forms.CharField(validators=[CharLimitValidator(models.NARRATIVE_CHAR_LIMITS[2])], label =  mark_safe(models.NARRATIVE_TEXTS[2]), widget= forms.Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(models.NARRATIVE_CHAR_LIMITS[2]) + ')'}))
  narrative3 = forms.CharField(validators=[CharLimitValidator(models.NARRATIVE_CHAR_LIMITS[3])], label =  mark_safe(models.NARRATIVE_TEXTS[3]), widget= forms.Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(models.NARRATIVE_CHAR_LIMITS[3]) + ')'}))
  narrative4 = forms.CharField(validators=[CharLimitValidator(models.NARRATIVE_CHAR_LIMITS[4])], label =  mark_safe(models.NARRATIVE_TEXTS[4]), widget= forms.Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(models.NARRATIVE_CHAR_LIMITS[4]) + ')'}))
  narrative5 = forms.CharField(validators=[CharLimitValidator(models.NARRATIVE_CHAR_LIMITS[5])], label =  mark_safe(models.NARRATIVE_TEXTS[5]), widget= forms.Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(models.NARRATIVE_CHAR_LIMITS[5]) + ')'}))
  narrative6 = forms.CharField(validators=[CharLimitValidator(models.NARRATIVE_CHAR_LIMITS[6])], label =  mark_safe(models.NARRATIVE_TEXTS[6]), widget= forms.Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(models.NARRATIVE_CHAR_LIMITS[6]) + ')'}))
  cycle_question = forms.CharField(validators=[CharLimitValidator(models.NARRATIVE_CHAR_LIMITS[7])], required=False, widget=forms.Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(models.NARRATIVE_CHAR_LIMITS[7]) + ')'}))
  
  #timeline (goes after narrative 4)
  timeline_1_date = forms.CharField(max_length = 50, widget= forms.Textarea(attrs={'rows':'5', 'cols':'20'}))
  timeline_1_activities = forms.CharField(widget= forms.Textarea(attrs={'rows':'5'}))
  timeline_1_goals = forms.CharField(widget= forms.Textarea(attrs={'rows':'5'}))
  timeline_2_date = forms.CharField(max_length = 50, widget= forms.Textarea(attrs={'rows':'5', 'cols':'20'}), required=False)
  timeline_2_activities = forms.CharField(widget= forms.Textarea(attrs={'rows':'5'}), required=False)
  timeline_2_goals = forms.CharField(widget= forms.Textarea(attrs={'rows':'5'}), required=False)
  timeline_3_date = forms.CharField(max_length = 50, widget= forms.Textarea(attrs={'rows':'5', 'cols':'20'}), required=False)
  timeline_3_activities = forms.CharField(widget= forms.Textarea(attrs={'rows':'5'}), required=False)
  timeline_3_goals = forms.CharField(widget= forms.Textarea(attrs={'rows':'5'}), required=False)
  timeline_4_date = forms.CharField(max_length = 50, widget= forms.Textarea(attrs={'rows':'5', 'cols':'20'}), required=False)
  timeline_4_activities = forms.CharField(widget= forms.Textarea(attrs={'rows':'5'}), required=False)
  timeline_4_goals = forms.CharField(widget= forms.Textarea(attrs={'rows':'5'}), required=False)
  timeline_5_date = forms.CharField(max_length = 50, widget= forms.Textarea(attrs={'rows':'5', 'cols':'20'}), required=False)
  timeline_5_activities = forms.CharField(widget= forms.Textarea(attrs={'rows':'5'}), required=False)
  timeline_5_goals = forms.CharField(widget= forms.Textarea(attrs={'rows':'5'}), required=False)
  
  #collab references (after narrative 5)
  collab_ref1_name = forms.CharField(help_text='Provide names and contact information for two people who are familiar with your organization\'s role in these collaborations so we can contact them for more information.', label='Name', max_length = 150)
  collab_ref1_org = forms.CharField(label='Organization', max_length = 150)
  collab_ref1_phone = forms.CharField(label='Phone number',  max_length = 20, required=False)
  collab_ref1_email = forms.EmailField(label='Email', required=False)
  
  collab_ref2_name = forms.CharField(label='Name', max_length = 150)
  collab_ref2_org = forms.CharField(label='Organization', max_length = 150)
  collab_ref2_phone = forms.CharField(label='Phone number',  max_length = 20, required=False)
  collab_ref2_email = forms.EmailField(label='Email', required=False)
  
  #racial justice references (after narrative 6)
  racial_justice_ref1_name = forms.CharField(help_text='If you are a primarily white-led organization, please list at least one organization led by people of color that we can contact as a reference for your racial justice work.', label='Name', max_length = 150, required=False)
  racial_justice_ref1_org = forms.CharField(label='Organization', max_length = 150, required=False)
  racial_justice_ref1_phone = forms.CharField(label='Phone number', max_length = 20, required=False)
  racial_justice_ref1_email = forms.EmailField(label='Email', required=False)
 
  racial_justice_ref2_name = forms.CharField(label='Name', max_length = 150, required=False)
  racial_justice_ref2_org = forms.CharField(label='Organization', max_length = 150, required=False)
  racial_justice_ref2_phone = forms.CharField(label='Phone number',  max_length = 20, required=False)
  racial_justice_ref2_email = forms.EmailField(label='Email', required=False) 
  
  #files
  demographics = forms.FileField(label = 'Diversity chart', max_length=255, validators=[validate_file_extension], widget=forms.FileInput(attrs={'onchange':'fileChanged(this.id);'}))
  funding_sources = forms.FileField(label = 'Funding sources', max_length=255, validators=[validate_file_extension], widget=forms.FileInput(attrs={'onchange':'fileChanged(this.id);'}))
  fiscal_letter = forms.FileField(required=False, label = 'Fiscal sponsor letter', help_text='Letter from the sponsor stating that it agrees to act as your fiscal sponsor and supports Social Justice Fund\'s mission.', validators=[validate_file_extension], max_length=255, widget=forms.FileInput(attrs={'onchange':'fileChanged(this.id);'}))
  budget = forms.FileField(max_length=255, validators=[validate_file_extension], widget=forms.FileInput(attrs={'onchange':'fileChanged(this.id);'}), required=False)
  budget1 = forms.FileField(max_length=255, label = 'Annual statement', validators=[validate_file_extension], widget=forms.FileInput(attrs={'onchange':'fileChanged(this.id);'}), required=False)
  budget2 = forms.FileField(max_length=255, label = 'Annual operating budget', validators=[validate_file_extension], widget=forms.FileInput(attrs={'onchange':'fileChanged(this.id);'}), required=False)
  budget3 = forms.FileField(max_length=255, label = 'Balance sheet (if available)', validators=[validate_file_extension], widget=forms.FileInput(attrs={'onchange':'fileChanged(this.id);'}), required=False)
  project_budget_file = forms.FileField(max_length=255, label = 'Project budget', validators=[validate_file_extension], widget=forms.FileInput(attrs={'onchange':'fileChanged(this.id);'}), required=False)
  
  def __init__(self, cycle, *args, **kwargs):
    super(GrantApplicationForm, self).__init__(*args, **kwargs)
    if cycle and cycle.extra_question:
      self.fields['cycle_question'].required = True
      logging.info('Requiring the cycle question')
      
  def clean(self):
    cleaned_data = super(GrantApplicationForm, self).clean()
    logging.info('========= form clean method, data is: ' + str(cleaned_data))
    
    #project - require title & budget if type
    support_type = cleaned_data.get('support_type')
    if support_type == 'Project support':
      if not cleaned_data.get('project_budget'):
        self._errors["project_budget"] = '<div class="form_error">This field is required.</div>'
      if not cleaned_data.get('project_title'):
        self._errors["project_title"] = '<div class="form_error">This field is required.</div>'

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
         self._errors["project_budget_file"] = '<div class="form_error">This field is required.</div>'
    """
    elif b1 or b2 or b3: #all-in-one included + other file(s)
      self._errors["budget"] = '<div class="form_error">Budget documents are required. You may upload them as one file or as multuple files.</div>'
    """      

    #fiscal info/file - require all if any
    org = cleaned_data.get('fiscal_org')
    person = cleaned_data.get('fiscal_person')
    phone = cleaned_data.get('fiscal_telephone')
    email = cleaned_data.get('fiscal_email')
    address = cleaned_data.get('fiscal_address')
    file = cleaned_data.get('fiscal_letter')
    if (org or person or phone or email or address):
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
      if not file:
        self._errors["fiscal_letter"] = '<div class="form_error">This field is required.</div>'

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
      
    return cleaned_data

class RolloverForm(forms.Form):
  """Fields created on init:
  application - any of org's submitted apps
  draft - any of org's drafts
  cycle - any open cycle that does not have a submission or draft
  """
  
  def __init__(self, organization, *args, **kwargs):
    super(RolloverForm, self).__init__(*args, **kwargs)
    
    #get apps & drafts
    submitted = models.GrantApplication.objects.filter(organization=organization).order_by('-submission_time').select_related('grant_cycle')
    drafts = models.DraftGrantApplication.objects.filter(organization=organization).select_related('grant_cycle')
    
    #filter out their cycles, get rest of open ones
    exclude_cycles = [d.grant_cycle.pk for d in drafts] + [a.grant_cycle.pk for a in submitted]
    cycles = models.GrantCycle.objects.filter(open__lt = timezone.now(), close__gt = timezone.now()).exclude(id__in=exclude_cycles)
    
    #create fields
    self.fields['application'] = forms.ChoiceField(choices = [('', '--- Submitted applications ---')] + [(a.id, str(a.grant_cycle) + ' - submitted ' + datetime.datetime.strftime(a.submission_time, '%m/%d/%y')) for a in submitted], required=False, initial = 0)
    self.fields['draft'] = forms.ChoiceField(choices = [('', '--- Saved drafts ---')] + [(d.id, str(d.grant_cycle) + ' - modified ' + datetime.datetime.strftime(d.modified, '%m/%d/%y')) for d in drafts], required=False, initial = 0)
    self.fields['cycle'] = forms.ChoiceField(choices = [('', '--- Open cycles ---')] + [(c.id, str(c)) for c in cycles])
  
  def clean(self):
    cleaned_data = super(RolloverForm, self).clean()
    cycle = cleaned_data.get('cycle')
    application = cleaned_data.get('application')
    draft = cleaned_data.get('draft')
    if not cycle:
      self._errors["cycle"] = self.error_class(["Required."])
    else: #check cycle is still open
      try:
        cycle_obj = models.GrantCycle.objects.get(pk = int(cycle))
      except models.GrantCycle.DoesNotExist:
        logging.error("RolloverForm submitted cycle does not exist")
        self._errors["cycle"] = self.error_class(["Internal error, please try again."])
      if not cycle_obj.is_open:
        self._errors["cycle"] = self.error_class(["That cycle has closed.  Select a different one."])
    if not draft and not application:
      self._errors["draft"] = self.error_class(["Select one."])
    elif draft and application:
      self._errors["draft"] = self.error_class(["Select only one."])
    return cleaned_data
