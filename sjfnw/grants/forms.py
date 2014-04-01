﻿from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.safestring import mark_safe

from sjfnw.fund.models import GivingProject
from sjfnw.grants.models import Organization, GrantCycle, GrantApplication, DraftGrantApplication, STATE_CHOICES, SCREENING, PRE_SCREENING

import datetime, logging

logger = logging.getLogger('sjfnw')


class LoginForm(forms.Form):
  email = forms.EmailField(max_length=255)
  password = forms.CharField(widget=forms.PasswordInput())

class RegisterForm(forms.Form):
  email = forms.EmailField(max_length=255)
  password = forms.CharField(widget=forms.PasswordInput())
  passwordtwo = forms.CharField(widget=forms.PasswordInput(),
                                label="Re-enter password")
  organization = forms.CharField()

  def clean(self):
    cleaned_data = super(RegisterForm, self).clean()
    # make sure org is not already registered
    org = cleaned_data.get('organization')
    email = cleaned_data.get('email')
    if org and email:
      if Organization.objects.filter(email = email):
        logger.warning(org + 'tried to re-register with ' + email)
        raise ValidationError('That email is already registered. Log in instead.')
      name_match = Organization.objects.filter(name = org)
      if name_match:
        if name_match[0].email:
          logger.warning('Name match on registration, emails diff: ' + org)
          raise ValidationError('That organization is already registered. Log in instead.')
        else: #name match, blank email
          logger.warning('Name match, blank email. ' + org)
      # check if User already exists
      if User.objects.filter(username = email):
        logger.warning('User already exists, but not Org: ' + email)
        raise ValidationError('That email is registered with Project Central.'
                              ' Please register using a different email.')
      # make sure passwords match
      password = cleaned_data.get("password")
      passwordtwo = cleaned_data.get("passwordtwo")
      if password and passwordtwo and password != passwordtwo:
        raise ValidationError('Passwords did not match.')
    return cleaned_data


class CheckMultiple(forms.widgets.CheckboxSelectMultiple):
  """ Adds links to javascript function to select all/none of options

  Subclasses CheckboxSelectMultiple; only modifies the render function
  """

  def render(self, name, value, attrs=None, choices = ()):
    rendered = super(CheckMultiple, self).render(name, value, attrs, choices)
    return mark_safe('[<a onclick="check(\'' + name +
        '\', true)">all</a>] [<a onclick="check(\'' + name +
        '\', false)">none</a>]' + rendered)


class RolloverForm(forms.Form): #used by org
  """ Used by organizations to copy a draft or app into another grant cycle
  
  Fields (created on init):
    application - any of org's submitted apps
    draft - any of org's drafts
    cycle - any open cycle that does not have a submission or draft
  """

  def __init__(self, organization, *args, **kwargs):
    super(RolloverForm, self).__init__(*args, **kwargs)

    #get apps & drafts
    submitted = GrantApplication.objects.filter(organization=organization).order_by('-submission_time').select_related('grant_cycle')
    drafts = DraftGrantApplication.objects.filter(organization=organization).select_related('grant_cycle')

    #filter out their cycles, get rest of open ones
    exclude_cycles = [d.grant_cycle.pk for d in drafts] + [a.grant_cycle.pk for a in submitted]
    cycles = GrantCycle.objects.filter(open__lt = timezone.now(), close__gt = timezone.now()).exclude(id__in=exclude_cycles)

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
        cycle_obj = GrantCycle.objects.get(pk = int(cycle))
      except GrantCycle.DoesNotExist:
        logger.error("RolloverForm submitted cycle does not exist")
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
    submitted = GrantApplication.objects.filter(organization=organization).order_by('-submission_time').select_related('grant_cycle')
    drafts = DraftGrantApplication.objects.filter(organization=organization).select_related('grant_cycle')

    #get last 6 mos of cycles
    cutoff = timezone.now() - datetime.timedelta(days=180)
    exclude_cycles = [d.grant_cycle.pk for d in drafts] + [a.grant_cycle.pk for a in submitted]
    cycles = GrantCycle.objects.filter(close__gt = cutoff).exclude(id__in=exclude_cycles)

    #create field
    self.fields['cycle'] = forms.ChoiceField(choices = [('', '--- Grant cycles ---')] + [(c.id, unicode(c)) for c in cycles])

class BaseOrgAppReport(forms.Form):
  """ Abstract form for fields shared between report types """

  # filters
  filter_org_name = forms.CharField(max_length=255, required=False,
      label='Organization name', 
      help_text='Organization name must contain the given text')

  filter_app_city = forms.CharField(label='City', max_length=255,
      required=False, help_text='City must match the given text')
  filter_app_state = forms.MultipleChoiceField(label='State',
      choices = STATE_CHOICES[:5],
      widget = forms.CheckboxSelectMultiple, required = False)
  filter_app_fiscal = forms.BooleanField(label='Has fiscal sponsor', 
      required=False)

  # fields
  report_app_contact = forms.MultipleChoiceField(
      label='Contact', required=False,
      widget = CheckMultiple, choices = [
        ('contact_person', 'Contact person name'),
        ('contact_person_title', 'Contact person title'),
        ('address', 'Address'),
        ('city', 'City'),
        ('state', 'State'),
        ('zip', 'ZIP'),
        ('telephone_number', 'Telephone number'),
        ('fax_number', 'Fax number'),
        ('email_address', 'Email address'),
        ('website', 'Website')
      ])
  report_app_org = forms.MultipleChoiceField(
      label='Organization', required=False,
      widget = CheckMultiple, choices = [
        ('status', 'Status'),
        ('ein', 'EIN'),
        ('founded', 'Year founded')
        ])
  report_app_fiscal = forms.BooleanField(label='Fiscal sponsor', required=False)

  #format (browse, csv)
  format = forms.ChoiceField(choices = [('csv', 'CSV'), ('browse', 'Don\'t export, just browse')])

  class Meta:
    abstract = True

class AppReportForm(BaseOrgAppReport):

  #filters
  filter_year_min = forms.ChoiceField(
      choices = [(n, n) for n in range(timezone.now().year, 1990, -1)],
      initial = timezone.now().year-1)
  filter_year_max = forms.ChoiceField(
      choices =[(n, n) for n in range(timezone.now().year, 1990, -1)])
  filter_pre_screening = forms.MultipleChoiceField(label='Pre-screening status',
      choices = PRE_SCREENING,
      widget = forms.CheckboxSelectMultiple, required = False)
  filter_screening_status = forms.MultipleChoiceField(label='Giving project screening status',
      choices = SCREENING,
      widget = forms.CheckboxSelectMultiple, required = False)
  filter_giving_projects = forms.MultipleChoiceField(label='Giving projects',
      choices = [], widget = forms.CheckboxSelectMultiple, required = False)
  filter_grant_cycle = forms.MultipleChoiceField(choices = [],
                                          widget = forms.CheckboxSelectMultiple,
                                          required = False)
  filter_poc_bonus = forms.BooleanField(required=False)
  filter_geo_bonus = forms.BooleanField(required=False)
  #awarded = forms.BooleanField(required=False)

  #fields
  #always: organization, grant cycle, submission time
  report_basics = forms.MultipleChoiceField(
      label='Basics', required=False,
      widget = CheckMultiple, choices = [
        ('id', 'Unique id number'),
        ('giving_projects', 'Giving projects'),
        ('pre_screening_status', 'Pre-screening status')
      ])
  report_proposal = forms.MultipleChoiceField(
      label='Grant request and project', required=False,
      widget = CheckMultiple, choices = [
        ('amount_requested', 'Amount requested'),
        ('grant_request', 'Description of grant request'),
        ('support_type', 'Support type'),
        ('grant_period', 'Grant period'),
        ('project_title', 'Project title'),
        ('project_budget', 'Project budget'),
        ('previous_grants', 'Previous grants from SJF')
      ])
  report_budget = forms.MultipleChoiceField(
      label='Budget', required=False,
      widget = CheckMultiple, choices = [
        ('start_year', 'Start of fiscal year'),
        ('budget_last', 'Budget last year'),
        ('budget_current', 'Budget current year')
      ])
  report_collab = forms.BooleanField(label='Collaboration references',
      required=False)
  report_racial_ref = forms.BooleanField(label='Racial justice references',
      required=False)
  report_bonuses = forms.BooleanField(label='Scoring bonuses', required=False)
  report_gp_screening = forms.BooleanField(label='GP screening status', required=False)
  report_award = forms.BooleanField(label='Grant awards', required=False)

  def __init__(self, *args, **kwargs):
    super(AppReportForm, self).__init__(*args, **kwargs)

    #get projects
    choices = GivingProject.objects.values_list('title', flat = True)
    choices = set(choices)
    choices = [(g, g) for g in choices]
    self.fields['filter_giving_projects'].choices = choices

    #get cycles
    choices = GrantCycle.objects.values_list('title', flat = True)
    choices = set(choices)
    choices = [(g, g) for g in choices]
    self.fields['filter_grant_cycle'].choices = choices

  def clean(self):
    cleaned_data = super(AppReportForm, self).clean()
    if cleaned_data['filter_year_max'] < cleaned_data['filter_year_min']:
      raise ValidationError('Start year must be less than or equal to end year.')
    return cleaned_data


class AwardReportForm(BaseOrgAppReport):

  # filters
  filter_year_min = forms.ChoiceField(
      choices = [(n, n) for n in range(timezone.now().year, 1990, -1)],
      initial = timezone.now().year-1)
  filter_year_max = forms.ChoiceField(choices =
      [(n, n) for n in range(timezone.now().year, 1990, -1)])

  # fields (always: org name, amount, check_mailed)
  report_id = forms.BooleanField(required=False, label='ID number',
      help_text='Only applies to sponsored program grants')
  report_check_number = forms.BooleanField(required=False, label='Check number')
  report_date_approved = forms.BooleanField(required=False,
      label='Date approved by E.D.')
  report_agreement_dates = forms.BooleanField(required=False,
      label='Date agreement mailed/returned',
      help_text='Only applies to giving project grants')
  report_year_end_report_due = forms.BooleanField(required=False,
      label='Date year end report due',
      help_text='Only applies to giving project grants')

  def clean(self):
    cleaned_data = super(AwardReportForm, self).clean()
    if cleaned_data['year_max'] < cleaned_data['year_min']:
      raise ValidationError('Start year must be less than or equal to end year.')
    return cleaned_data


class OrgReportForm(BaseOrgAppReport):

  # filters
  filter_registered = forms.ChoiceField(choices = [('None', '---'), ('True', 'yes'), ('False', 'no')])

  # fields
  report_staff_contact = forms.MultipleChoiceField(label='Staff-entered contact info',
      required = False, widget = CheckMultiple, choices = [
        ('contact_person', 'Contact person name'),
        ('contact_person_title', 'Contact person title'),
        ('phone', 'Telephone number'),
        ('email_address', 'Email address')
      ])
  report_account_email = forms.BooleanField(label='Login email',
      required=False)
  report_applications = forms.BooleanField(label='List of applications',
      required=False)
  report_awards = forms.BooleanField(label='List of awards',
      required=False)


class LoginAsOrgForm(forms.Form):

  def __init__(self, *args, **kwargs):
    super(LoginAsOrgForm, self).__init__(*args, **kwargs)

    orgs = Organization.objects.order_by('name')
    self.fields['organization'] = forms.ChoiceField(choices = 
        [('', '--- Organizations ---')] + [(o.email, unicode(o)) for o in orgs])

