from django import forms
from django.core import validators
from django.utils import timezone
from sjfnw.forms import IntegerCommaField
from sjfnw.fund import models
import logging

logger = logging.getLogger('sjfnw')


class LoginForm(forms.Form):
  email = forms.EmailField(max_length=100)
  password = forms.CharField(widget=forms.PasswordInput())

class RegistrationForm(forms.Form):
  first_name = forms.CharField(max_length=100)
  last_name = forms.CharField(max_length=100)
  email = forms.EmailField(max_length=100)
  password = forms.CharField(widget=forms.PasswordInput())
  passwordtwo = forms.CharField(widget=forms.PasswordInput(),
                                label="Re-enter password")
  giving_project = forms.ModelChoiceField(queryset=models.GivingProject.objects.filter(fundraising_deadline__gte=timezone.now().date(), public=True),
                                          empty_label="Select a giving project",
                                          required=False)

  def clean(self): #make sure passwords match
    cleaned_data = super(RegistrationForm, self).clean()
    password = cleaned_data.get("password")
    passwordtwo = cleaned_data.get("passwordtwo")
    if password and passwordtwo and password != passwordtwo:
      self._errors["password"] = self.error_class(["Passwords did not match."])
      del cleaned_data["password"]
      del cleaned_data["passwordtwo"]
    return cleaned_data

class AddProjectForm(forms.Form):
  giving_project = forms.ModelChoiceField(queryset=models.GivingProject.objects.filter(fundraising_deadline__gte=timezone.now().date(), public=True),
                                          empty_label="Select a giving project")

class MassDonor(forms.Form):
  firstname = forms.CharField(max_length=100, label='*First name')
  lastname = forms.CharField(max_length=100, required=False, label='Last name')
  amount = IntegerCommaField(label='*Estimated donation ($)',
                             widget=forms.TextInput(attrs={'class':'tq'}))
  likelihood = forms.IntegerField(label='*Estimated likelihood (%)',
                                  validators=[validators.MaxValueValidator(100)],
                                  widget=forms.TextInput(attrs={'class':'half'}))

class MassDonorPre(forms.Form):
  firstname = forms.CharField(max_length=100, label='*First name')
  lastname = forms.CharField(max_length=100, required=False, label='Last name')

class DonorEstimates(forms.Form):
  donor = forms.ModelChoiceField(queryset=models.Donor.objects.all(),
                                 widget=forms.HiddenInput())
  amount = IntegerCommaField(label='*Estimated donation ($)',
                             widget=forms.TextInput(attrs={'class':'tq'}))
  likelihood = forms.IntegerField(label='*Estimated likelihood (%)',
                                  validators=[validators.MaxValueValidator(100)],
                                  widget=forms.TextInput(attrs={'class':'half'}))

class MassStep(forms.Form):
  date = forms.DateField(required=False,
                         widget=forms.DateInput(attrs={'class':'datePicker'},
                         format = '%m/%d/%Y'),
                         error_messages = {'invalid':'Please enter a date in mm/dd/yyyy format.'})
  description = forms.CharField(max_length=255, required=False,
                                widget=forms.TextInput(attrs={'onfocus':'showSuggestions(this.id)'}))
  donor = forms.ModelChoiceField(queryset=models.Donor.objects.all(),
                                 widget=forms.HiddenInput())

  def clean(self): #date/desc pair validation
    cleaned_data = super(MassStep, self).clean()
    date = cleaned_data.get("date")
    desc = cleaned_data.get("description")
    msg = "This field is required."
    if date:
      if not desc: #date, no desc - invalid
        self._errors["description"] = self.error_class([msg])
    elif desc: # desc, no date - invalid
      self._errors["date"] = self.error_class(['Please enter a date in mm/dd/yyyy format.'])
    else: #neither - valid, but not wanted in data
      cleaned_data = []
    return cleaned_data

class StepDoneForm(forms.Form):
  asked = forms.BooleanField(required=False,
                             widget=forms.CheckboxInput(attrs={'onchange':'askedToggled(this)'}))
  response = forms.ChoiceField(choices=((1, 'Promised'), (2, 'Unsure'), (3, 'Declined')),
                               initial=2,
                               widget=forms.Select(attrs={'onchange':'responseSelected(this)'}))
  promised_amount = IntegerCommaField(required=False, min_value=0,
                                      error_messages={'min_value': 'Promise amounts cannot be negative'},
                                      widget=forms.TextInput(attrs = {'onchange':'promiseEntered(this)', 'size':10}))

  last_name = forms.CharField(max_length=255, required=False)
  phone = forms.CharField(max_length=15, required=False)
  email = forms.EmailField(required=False)

  notes = forms.CharField(max_length=255, required=False,
                          widget=forms.Textarea(attrs={'rows':3, 'cols':20}))

  next_step = forms.CharField(max_length=100, required=False)
  next_step_date = forms.DateField(required=False,
                                   widget=forms.DateInput(
                                     attrs={'class':'datePicker', 'input_formats':"['%m/%d/%Y', '%m-%d-%Y', '%n/%j/%Y', '%n-%j-%Y']"},
                                     format = '%m/%d/%Y'),
                                   error_messages = {'invalid':'Please enter a date in mm/dd/yyyy format.'})

  def clean(self):
    cleaned_data = super(StepDoneForm, self).clean()
    response = cleaned_data.get("response")
    amt = cleaned_data.get("promised_amount")
    next_step = cleaned_data.get("next_step")
    next_step_date = cleaned_data.get("next_step_date")
    last_name = cleaned_data.get("last_name")
    phone = cleaned_data.get("phone")
    email = cleaned_data.get("email")

    if response == '1': #response = promise
      if not amt or amt == 0: #no/zero amount entered
        logger.debug('Promised without amount')
        self._errors["promised_amount"] = self.error_class(["Enter an amount."])
      if not last_name:
        logger.debug('Promised without last name')
        self._errors["last_name"] = self.error_class(["Enter a last name."])
      if not phone and not email:
        logger.debug('Promised without contact info')
        self._errors["phone"] = self.error_class(["Enter a phone number or email."])
    if next_step and not next_step_date: #next step - date missing
      self._errors["next_step_date"] = self.error_class(["Enter a date in mm/dd/yyyy format."])
      del cleaned_data["next_step"]
    elif next_step_date and not next_step: #next step - desc missing
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

