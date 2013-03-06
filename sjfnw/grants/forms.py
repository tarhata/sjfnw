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
    logging.info(organization)
    super(RolloverForm, self).__init__(*args, **kwargs)
    self.fields['application'] = forms.ChoiceField(choices=[(a.id, str(a.grant_cycle) + ' - submitted ' + datetime.datetime.strftime(a.submission_time, '%m-%d-%Y')) for a in models.GrantApplication.objects.filter(organization = organization)] + [(0, '------')], required=False, initial = 0)
    self.fields['draft'] = forms.ChoiceField(choices= [(d.id, str(d.grant_cycle) + ' - draft modified ' + datetime.datetime.strftime(d.modified, '%m-%d-%Y')) for d in models.DraftGrantApplication.objects.filter(organization = organization)] + [(0, '------')], required=False, initial = 0)
    self.fields['cycle'] = forms.ChoiceField(choices=[(c.id, str(c)) for c in models.GrantCycle.objects.filter(open__lt = timezone.now(), close__gt = timezone.now())])
  
  def clean(self):
    cleaned_data = super(RolloverForm, self).clean()
    #don't let both draft and app be 0
    #don't let both draft and app be non-0
    return cleaned_data