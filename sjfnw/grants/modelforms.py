from django import forms
from django.forms import ValidationError, ModelForm
from django.utils.text import capfirst

from sjfnw.forms import IntegerCommaField, PhoneNumberField
from sjfnw.grants.models import Organization, GrantApplication, DraftGrantApplication

import json, logging
logger = logging.getLogger('sjfnw')



class OrgProfile(ModelForm):
  class Meta:
    model = Organization
    exclude = ('name', 'email')


class TimelineWidget(forms.widgets.MultiWidget):
  def __init__(self, attrs=None):
    _widgets = (
      forms.Textarea(attrs={'rows':'5', 'cols':'20'}),
      forms.Textarea(attrs={'rows':'5'}),
      forms.Textarea(attrs={'rows':'5'}),
      forms.Textarea(attrs={'rows':'5', 'cols':'20'}),
      forms.Textarea(attrs={'rows':'5'}),
      forms.Textarea(attrs={'rows':'5'}),
      forms.Textarea(attrs={'rows':'5', 'cols':'20'}),
      forms.Textarea(attrs={'rows':'5'}),
      forms.Textarea(attrs={'rows':'5'}),
      forms.Textarea(attrs={'rows':'5', 'cols':'20'}),
      forms.Textarea(attrs={'rows':'5'}),
      forms.Textarea(attrs={'rows':'5'}),
      forms.Textarea(attrs={'rows':'5', 'cols':'20'}),
      forms.Textarea(attrs={'rows':'5'}),
      forms.Textarea(attrs={'rows':'5'}),
    )
    super(TimelineWidget, self).__init__(_widgets, attrs)


  def decompress(self, value):
    """ break single database value up for widget display
          argument: database value (json string representing list of vals)
          returns: list of values to be displayed in widgets """

    if value:
      return json.loads(value)
    return [None, None, None, None, None, None, None, None,
            None, None, None, None, None, None, None]


  def format_output(self, rendered_widgets):
    """
    format the widgets for display
      args: list of rendered widgets
      returns: a string of HTML for displaying the widgets
    """

    html = ('<table id="timeline_form"><tr class="heading"><td></td>'
            '<th>Date range</th><th>Activities<br><i>(What will you be doing?)</i></th>'
            '<th>Goals/objectives<br><i>(What do you hope to achieve?)</i></th></tr>')
    for i in range(0, len(rendered_widgets), 3):
      html += ('<tr><th class="left">Quarter ' + str((i+3)/3) + '</th><td>' +
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

class GrantApplicationModelForm(forms.ModelForm):

  formfield_callback = custom_fields

  class Meta:
    model = GrantApplication
    exclude = ['pre_screening_status', 'submission_time', 'giving_projects']
    widgets = {
      #char limits
      'mission': forms.Textarea(attrs={'rows': 3, 'onKeyUp':'charLimitDisplay(this, 150)'}),
      'grant_request': forms.Textarea(attrs={'rows': 3, 'onKeyUp':'charLimitDisplay(this, 100)'}),
      'narrative1': forms.Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(GrantApplication.NARRATIVE_CHAR_LIMITS[1]) + ')'}),
      'narrative2': forms.Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(GrantApplication.NARRATIVE_CHAR_LIMITS[2]) + ')'}),
      'narrative3': forms.Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(GrantApplication.NARRATIVE_CHAR_LIMITS[3]) + ')'}),
      'narrative4': forms.Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(GrantApplication.NARRATIVE_CHAR_LIMITS[4]) + ')'}),
      'narrative5': forms.Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(GrantApplication.NARRATIVE_CHAR_LIMITS[5]) + ')'}),
      'narrative6': forms.Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(GrantApplication.NARRATIVE_CHAR_LIMITS[6]) + ')'}),
      'cycle_question': forms.Textarea(attrs={'onKeyUp':'charLimitDisplay(this, ' + str(GrantApplication.NARRATIVE_CHAR_LIMITS[7]) + ')'}),
      #file callbacks
      'budget': forms.FileInput(attrs={'onchange':'fileChanged(this.id);'}),
      'demographics': forms.FileInput(attrs={'onchange':'fileChanged(this.id);'}),
      'funding_sources': forms.FileInput(attrs={'onchange':'fileChanged(this.id);'}),
      'fiscal_letter': forms.FileInput(attrs={'onchange':'fileChanged(this.id);'}),
      'budget1': forms.FileInput(attrs={'onchange':'fileChanged(this.id);'}),
      'budget2': forms.FileInput(attrs={'onchange':'fileChanged(this.id);'}),
      'budget3': forms.FileInput(attrs={'onchange':'fileChanged(this.id);'}),
      'project_budget_file': forms.FileInput(attrs={'onchange':'fileChanged(this.id);'}),
      #timeline
      'timeline':TimelineWidget(),
    }

  def __init__(self, cycle, *args, **kwargs):
    super(GrantApplicationModelForm, self).__init__(*args, **kwargs)
    if cycle and cycle.extra_question:
      self.fields['cycle_question'].required = True
      logger.info('Requiring the cycle question')

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


# ADMIN

class DraftAdminForm(ModelForm):
  class Meta:
    model = DraftGrantApplication

  def clean(self):
    cleaned_data = super(DraftAdminForm, self).clean()
    org = cleaned_data.get('organization')
    cycle = cleaned_data.get('grant_cycle')
    if org and cycle:
      if GrantApplication.objects.filter(organization=org, grant_cycle=cycle):
        raise ValidationError('This organization has already submitted an '
                              'application to this grant cycle.')
    return cleaned_data


