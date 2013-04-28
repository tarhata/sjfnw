from django import forms
from django.conf import settings
from django.utils import timezone
from django.utils.safestring import mark_safe
from fund.models import GivingProject
import models, datetime, logging

class LoginForm(forms.Form):
  email = forms.EmailField(max_length=255)
  password = forms.CharField(widget=forms.PasswordInput())

class RegisterForm(forms.Form):
  email = forms.EmailField(max_length=255)
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

class RolloverForm(forms.Form): #used by org
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
    self.fields['draft'] = forms.ChoiceField(choices = [('', '--- Saved drafts ---')] + [(d.id, unicode(d.grant_cycle) + ' - modified ' + datetime.datetime.strftime(d.modified, '%m/%d/%y')) for d in drafts], required=False, initial = 0)
    self.fields['cycle'] = forms.ChoiceField(choices = [('', '--- Open cycles ---')] + [(c.id, unicode(c)) for c in cycles])
  
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

class AdminRolloverForm(forms.Form):

  def __init__(self, organization, *args, **kwargs):
    super(AdminRolloverForm, self).__init__(*args, **kwargs)
    
    #get apps & drafts (for eliminating cycles)
    submitted = models.GrantApplication.objects.filter(organization=organization).order_by('-submission_time').select_related('grant_cycle')
    drafts = models.DraftGrantApplication.objects.filter(organization=organization).select_related('grant_cycle')
    
    #get last 6 mos of cycles
    cutoff = timezone.now() - datetime.timedelta(days=180)
    exclude_cycles = [d.grant_cycle.pk for d in drafts] + [a.grant_cycle.pk for a in submitted]
    cycles = models.GrantCycle.objects.filter(close__gt = cutoff).exclude(id__in=exclude_cycles)
    
    #create field
    self.fields['cycle'] = forms.ChoiceField(choices = [('', '--- Grant cycles ---')] + [(c.id, unicode(c)) for c in cycles])

class AppSearchForm(forms.Form):
  #filters
  year_min = forms.ChoiceField(choices = [(n, n) for n in range(timezone.now().year, 1990, -1)])
  year_max = forms.ChoiceField(choices =[(n, n) for n in range(timezone.now().year, 1990, -1)])
  screening_status = forms.MultipleChoiceField(choices = models.GrantApplication.SCREENING_CHOICES, widget = forms.CheckboxSelectMultiple, required = False)

  organization = forms.CharField(max_length=255, required=False)
  city = forms.CharField(max_length=255, required=False)
  state = forms.MultipleChoiceField(choices = models.STATE_CHOICES, widget = forms.CheckboxSelectMultiple, required = False)
  giving_project = forms.MultipleChoiceField(choices = [], widget = forms.CheckboxSelectMultiple, required = False) #TODO
  grant_cycle = forms.MultipleChoiceField(choices = [], widget = forms.CheckboxSelectMultiple, required = False) #TODO -- indiv or "type"
  poc_bonus = forms.BooleanField(required=False)
  geo_bonus = forms.BooleanField(required=False)
  
  #fields
  #always: organization, grant cycle, submission time
  report_basics= forms.MultipleChoiceField(label='Basics', required=False, widget = forms.CheckboxSelectMultiple, choices = [
    ('id', 'Unique id number'),
    ('giving_project_id', 'Giving project'),
    ('screening_status', 'Screening status')])
  report_contact = forms.MultipleChoiceField(label='Contact', required=False, widget = forms.CheckboxSelectMultiple, choices = [
    ('contact_person', 'Contact person name'),
    ('contact_person_title', 'Contact person title'),
    ('address', 'Address'),
    ('city', 'City'),
    ('state', 'State'),
    ('zip', 'ZIP'),
    ('telephone_number', 'Telephone number'),
    ('fax_number', 'Fax number'),
    ('email_address', 'Email address'),
    ('website', 'Website')])
  report_org = forms.MultipleChoiceField(label='Organization', required=False, widget = forms.CheckboxSelectMultiple, choices = [  
    ('status', 'Status'),
    ('ein', 'EIN'),
    ('founded', 'Year founded')])
  report_proposal = forms.MultipleChoiceField(label='Grant request and project', required=False, widget = forms.CheckboxSelectMultiple, choices = [  
    ('amount_requested', 'Amount requested'),
    ('support_type', 'Support type'),
    ('grant_period', 'Grant period'),
    ('project_title', 'Project title'),
    ('project_budget', 'Project budget'),
    ('previous_grants', 'Previous grants from SJF')])
  report_budget = forms.MultipleChoiceField(label='Budget', required=False, widget = forms.CheckboxSelectMultiple, choices = [  
    ('start_year', 'Start of fiscal year'),
    ('budget_last', 'Budget last year'),
    ('budget_current', 'Budget current year'),
    ('grant_request', 'Description of grant request')])
 
  report_fiscal = forms.BooleanField(label='Fiscal sponsor', required=False)
  report_collab = forms.BooleanField(label='Collaboration references', required=False)
  report_racial_ref = forms.BooleanField(label='Racial justice references', required=False)
  report_bonuses = forms.BooleanField(label='POC-led and geographic diversity', required=False)
  
  #format (browse, csv, tsv)
  format = forms.ChoiceField(choices = [('csv', 'CSV'), ('tsv', 'TSV'), ('browse', 'Don\'t export, just browse')])
  
  def __init__(self, *args, **kwargs):
    super(AppSearchForm, self).__init__(*args, **kwargs)
    
    #get projects
    choices = GivingProject.objects.values_list('title', flat = True)
    choices = set(choices)
    choices = [(g, g) for g in choices]
    self.fields['giving_project'].choices = choices
    
    #get cycless
    choices = models.GrantCycle.objects.values_list('title', flat = True)
    choices = set(choices)
    choices = [(g, g) for g in choices]
    self.fields['grant_cycle'].choices = choices
    
  def clean(self):
    cleaned_data = super(AppSearchForm, self).clean()
    if cleaned_data['year_max'] < cleaned_data['year_min']:
      self._errors['year_min'] = [u'Start year must be less than end year.']
    return cleaned_data