from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
import models, datetime
from sjfnw.utils import IntegerCommaField

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
  if not str(value).lower().split(".")[-1] in settings.ALLOWED_FILE_TYPES:
    raise ValidationError(u'That file type is not supported.')

class GrantApplicationFormy(forms.Form):
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
  status = forms.ChoiceField(choices=models.STATUS_CHOICES)
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
  contact_person = forms.CharField(max_length=250, label= 'Name', help_text='Contact person for this grant application')
  contact_person_title = forms.CharField(max_length=100, label='Title')
  grant_period = forms.CharField(max_length=250, required=False, label='Grant period (if different than fiscal year)')
  amount_requested = IntegerCommaField(label='Amount requested $')
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
  narrative1 = forms.CharField(validators=[CharLimitValidator(models.NARRATIVE_CHAR_LIMITS[1])], label = models.NARRATIVE_TEXTS[1], widget= forms.Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(models.NARRATIVE_CHAR_LIMITS[1]) + ')'}))
  narrative2 = forms.CharField(validators=[CharLimitValidator(models.NARRATIVE_CHAR_LIMITS[2])], label = models.NARRATIVE_TEXTS[2], widget= forms.Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(models.NARRATIVE_CHAR_LIMITS[2]) + ')'}))
  narrative3 = forms.CharField(validators=[CharLimitValidator(models.NARRATIVE_CHAR_LIMITS[3])], label = models.NARRATIVE_TEXTS[3], widget= forms.Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(models.NARRATIVE_CHAR_LIMITS[3]) + ')'}))
  narrative4 = forms.CharField(validators=[CharLimitValidator(models.NARRATIVE_CHAR_LIMITS[4])], label = models.NARRATIVE_TEXTS[4], widget= forms.Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(models.NARRATIVE_CHAR_LIMITS[4]) + ')'}))
  #timeline?

  narrative5 = forms.CharField(validators=[CharLimitValidator(models.NARRATIVE_CHAR_LIMITS[5])], label = models.NARRATIVE_TEXTS[5], widget= forms.Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(models.NARRATIVE_CHAR_LIMITS[5]) + ')'}))

  narrative6 = forms.CharField(validators=[CharLimitValidator(models.NARRATIVE_CHAR_LIMITS[6])], label = models.NARRATIVE_TEXTS[6], widget= forms.Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(models.NARRATIVE_CHAR_LIMITS[6]) + ')'}))
  cycle_question = forms.CharField(validators=[CharLimitValidator(models.NARRATIVE_CHAR_LIMITS[7])], required=False, widget=forms.Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(models.NARRATIVE_CHAR_LIMITS[7]) + ')'}))
  
  #references
  collab_ref1_name = forms.CharField(help_text='Provide names and contact information for two people who are familiar with your organization\'s role in these collaborations so we can contact them for more information.', label='Name', max_length = 150)
  collab_ref1_org = forms.CharField(label='Organization', max_length = 150)
  collab_ref1_phone = forms.CharField(label='Phone number',  max_length = 20, required=False)
  collab_ref1_email = forms.EmailField(label='Email', required=False)
  
  collab_ref2_name = forms.CharField(label='Name', max_length = 150)
  collab_ref2_org = forms.CharField(label='Organization', max_length = 150)
  collab_ref2_phone = forms.CharField(label='Phone number',  max_length = 20, required=False)
  collab_ref2_email = forms.EmailField(label='Email', required=False)
  
  racial_justice_ref1_name = forms.CharField(help_text='If you are a primarily white-led organization, also describe how you work as an ally to communities of color. Be as specific as possible, and list at least one organization led by people of color that we can contact as a reference for your racial justice work.', label='Name', max_length = 150, required=False)
  racial_justice_ref1_org = forms.CharField(label='Organization', max_length = 150, required=False)
  racial_justice_ref1_phone = forms.CharField(label='Phone number', max_length = 20, required=False)
  racial_justice_ref1_email = forms.EmailField(label='Email', required=False)
 
  racial_justice_ref2_name = forms.CharField(label='Name', max_length = 150, required=False)
  racial_justice_ref2_org = forms.CharField(label='Organization', max_length = 150, required=False)
  racial_justice_ref2_phone = forms.CharField(label='Phone number',  max_length = 20, required=False)
  racial_justice_ref2_email = forms.EmailField(label='Email', required=False) 
  
  #files
  budget = forms.FileField(max_length=255, validators=[validate_file_extension], widget=forms.FileInput(attrs={'onchange':'fileChanged(this.id);'}))
  demographics = forms.FileField(max_length=255, validators=[validate_file_extension], widget=forms.FileInput(attrs={'onchange':'fileChanged(this.id);'}))
  funding_sources = forms.FileField(max_length=255, validators=[validate_file_extension], widget=forms.FileInput(attrs={'onchange':'fileChanged(this.id);'}))
  fiscal_letter = forms.FileField(required=False, label = 'Fiscal sponsor letter', help_text='Letter from the sponsor stating that it agrees to act as your fiscal sponsor and supports Social Justice Fund\'s mission.', validators=[validate_file_extension], max_length=255, widget=forms.FileInput(attrs={'onchange':'fileChanged(this.id);'}))