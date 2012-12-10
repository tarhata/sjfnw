from django import forms
from django.forms import ModelForm
import models, datetime
from django.utils import timezone
import logging
from django.core.validators import MaxValueValidator

class LoginForm(forms.Form):
  email = forms.EmailField()
  password = forms.CharField(widget=forms.PasswordInput())

class RegistrationForm(forms.Form):
  first_name = forms.CharField(max_length=100)
  last_name = forms.CharField(max_length=100)
  email = forms.EmailField()
  password = forms.CharField(widget=forms.PasswordInput())
  giving_project = forms.ModelChoiceField(queryset=models.GivingProject.objects.filter(fundraising_deadline__gte=timezone.now().date()), empty_label="Select a giving project", required=False)

class AddProjectForm(forms.Form):
  giving_project = forms.ModelChoiceField(queryset=models.GivingProject.objects.filter(fundraising_deadline__gte=timezone.now().date()), empty_label="Select a giving project")

class NewDonor(forms.Form):
  firstname = forms.CharField(max_length=100, label='*First name')
  lastname = forms.CharField(max_length=100, required=False, label='Last name')
  amount = forms.IntegerField(label='*Estimated donation ($)')
  likelihood = forms.IntegerField(label='*Estimated likelihood (%)', validators=[MaxValueValidator(100)])
  phone = forms.CharField(max_length=15,required=False)
  email = forms.EmailField(required=False)

  step_date = forms.DateField(required=False, label='Date', widget=forms.DateInput(attrs={'class':'datePicker', 'readonly':'true'}, format='%Y-%m-%d'))
  step_desc = forms.CharField(required=False, max_length=255, label='Description')
  
  def clean(self): #step should be both empty or both entered
    logging.info("clean called on newdonor")
    cleaned_data = super(NewDonor, self).clean()
    date = cleaned_data.get("step_date")
    desc = cleaned_data.get("step_desc")
    msg = "This field is required."
    if date and not desc:
      self._errors["step_desc"] = self.error_class([msg])
      del cleaned_data["step_desc"]
    elif desc and not date:
      self._errors["step_date"] = self.error_class([msg])
      del cleaned_data["step_date"]
    return cleaned_data

class MassDonor(forms.Form):
  firstname = forms.CharField(max_length=100, label='*First name')
  lastname = forms.CharField(max_length=100, required=False, label='Last name')
  amount = forms.IntegerField(label='*Estimated donation ($)', widget=forms.TextInput(attrs={'class':'tq'}))
  likelihood = forms.IntegerField(label='*Estimated likelihood (%)', widget=forms.TextInput(attrs={'class':'half'}))

class MassStep(forms.Form):
  date = forms.DateField(widget=forms.DateInput(attrs={'class':'datePicker', 'readonly':'true'}, format='%Y-%m-%d'), required=False)
  description = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'onfocus':'showSuggestions(this.id)'}))
  donor = forms.ModelChoiceField(queryset=models.Donor.objects.all(), widget=forms.HiddenInput())
  
  def clean(self): #only require date or desc if the other is entered for that donor
    cleaned_data = super(MassStep, self).clean()
    date = cleaned_data.get("date")
    desc = cleaned_data.get("description")
    msg = "This field is required."
    if date:
      if not desc: #date, no desc - invalid
        self._errors["description"] = self.error_class([msg])
        del cleaned_data["description"]
    elif desc: # desc, no date - invalid
      self._errors["date"] = self.error_class([msg])
      del cleaned_data["date"]
    else: #neither - valid, but not wanted in data
      cleaned_data = []
    return cleaned_data
  
class StepDoneForm(forms.Form):
  asked = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'onchange':'askedToggled(this)'}))
  reply = forms.ChoiceField(choices=((1, 'Pledged'), (2, 'Unsure'), (3, 'Declined')), initial=2, widget=forms.Select(attrs={'onchange':'replySelected(this)'}))
  pledged_amount = forms.IntegerField(required=False, min_value=0, error_messages={'min_value': 'Pledge amounts cannot be negative'})
  notes = forms.CharField(max_length=255, required=False,  widget=forms.Textarea(attrs={'rows':2, 'cols':20}))
  next_step = forms.CharField(max_length=100, required=False)
  next_step_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'class':'datePicker', 'readonly':'true'}, format='%m/%d/%Y'))
  
  def clean(self): #if pledged, require amount
    cleaned_data = super(StepDoneForm, self).clean()
    reply = cleaned_data.get("reply")
    amt = cleaned_data.get("pledged_amount")
    next_step = cleaned_data.get("next_step")
    next_step_date = cleaned_data.get("next_step_date")
    
    if reply=='1' and (not amt or amt==0): #reply = pledge but no/zero amount entered
      logging.debug('Pledged without amount')
      self._errors["pledged_amount"] = self.error_class(["Please enter an amount."])
    elif reply=='3' and amt and amt>0: #declined but entered pledge amount
      logging.debug('Declined with amount')
      self._errors["pledged_amount"] = self.error_class(["Cannot enter a pledge amount with a declined response."])
      del cleaned_data["pledged_amount"]
    if next_step and not next_step_date:
      self._errors["next_step_date"] = self.error_class(["Enter a date."])
      del cleaned_data["next_step"]
    elif next_step_date and not next_step:
      self._errors["next_step"] = self.error_class(["Enter a description."])
      del cleaned_data["next_step_date"]
    return cleaned_data
    
class MembershipInlineFormset(forms.models.BaseInlineFormSet):
  def clean(self):
    # get forms that actually have valid data
    leader = 0
    for form in self.forms:
      try:
        if form.cleaned_data and not form.cleaned_data.get('DELETE', False) and form.cleaned_data['leader']:
          leader += 1
      except AttributeError:
        # annoyingly, if a subform is invalid Django explicity raises
        # an AttributeError for cleaned_data
        pass
    if leader < 1:
      raise forms.ValidationError('You must have at least one leader')