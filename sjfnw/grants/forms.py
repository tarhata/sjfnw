from django import forms
from django.utils import timezone
import models, datetime, logging

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
    if not draft and not application:
      self._errors["draft"] = self.error_class(["Select one."])
    elif draft and application:
      self._errors["draft"] = self.error_class(["Select only one."])
    return cleaned_data