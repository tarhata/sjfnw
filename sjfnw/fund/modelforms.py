from django.db import models
from django.forms import ModelForm, widgets

from sjfnw.forms import IntegerCommaField
from sjfnw.fund.models import Donor, Step, GPSurvey, GivingProject#, GPSurveyResponse

import json


def custom_integer_field(f, **kwargs):
  if f.verbose_name == '*Amount to ask ($)':
    return IntegerCommaField(**kwargs)
  else:
    return f.formfield()


def make_custom_datefield(f):
  """
  date selector implementation from
  http://strattonbrazil.blogspot.com/2011/03/using-jquery-uis-date-picker-on-all.html
  """
  formfield = f.formfield()
  if isinstance(f, models.DateField):
    formfield.error_messages['invalid'] = 'Please enter a date in mm/dd/yyyy format.'
    formfield.widget.format = '%m/%d/%Y'
    formfield.widget.input_formats = ['%m/%d/%Y', '%m-%d-%Y', '%n/%j/%Y',
                                      '%n-%j-%Y']
    formfield.widget.attrs.update({'class':'datePicker'})
  return formfield


class DonorForm(ModelForm): #used to edit, creation uses custom form
  formfield_callback = custom_integer_field

  class Meta:
    model = Donor
    fields = ('firstname', 'lastname', 'amount', 'likelihood', 'phone',
              'email', 'notes')
    widgets = {'notes': widgets.Textarea(attrs={'cols': 25, 'rows': 4})}


class DonorPreForm(ModelForm): #for editing prior to fund training

  class Meta:
    model = Donor
    fields = ('firstname', 'lastname', 'phone', 'email', 'notes')
    widgets = {'notes': widgets.Textarea(attrs={'cols': 25, 'rows': 4})}


class StepForm(ModelForm): #for adding a step
  formfield_callback = make_custom_datefield #date input

  class Meta:
    model = Step
    exclude = ('created', 'donor', 'completed', 'asked', 'promised')

class CreateQuestionsWidget(widgets.MultiWidget):

  def __init__(self, attrs=None):
    _widgets = []
    for i in range(1, 10):
      _widgets += [widgets.Select(choices = [(n, n) for n in range(1, 10)]),
                   widgets.Textarea(attrs = {'rows': 2}), 
                   widgets.Textarea(attrs = {'rows': 1, 'class': 'survey-choice'}),
                   widgets.Textarea(attrs = {'rows': 1, 'class': 'survey-choice'}),
                   widgets.Textarea(attrs = {'rows': 1, 'class': 'survey-choice'}),
                   widgets.Textarea(attrs = {'rows': 1, 'class': 'survey-choice'}),
                   widgets.Textarea(attrs = {'rows': 1, 'class': 'survey-choice'}),
                   widgets.Textarea(attrs = {'rows': 1, 'class': 'survey-choice'})]
    super(CreateQuestionsWidget, self).__init__(_widgets, attrs)
    

  def decompress(self, value):
    """ Takes single DB value, breaks it up for widget display """
    if value:
      return json.loads(value)
    else:
      return [None for widget in self.widgets]

  def format_output(self, rendered_widgets):
    """ Formats widgets for display.
    Returns HTML """
    html = ('<table id="survey-questions">'
            '<tr><th>Order</th><th>Title</th><th>Choices</th></tr>')
    for i in range(0, len(rendered_widgets), 8):
      html += ('<tr><td>' + rendered_widgets[i] + '</td><td>' + 
              rendered_widgets[i+1] + '</td><td>' + rendered_widgets[i+2] +
              rendered_widgets[i+3] + rendered_widgets[i+4] +
              rendered_widgets[i+5] + rendered_widgets[i+6] +
              rendered_widgets[i+7] + '</td></tr>')
    html += '</table>'
    return html


  def value_from_datadict(self, data, files, name):
    """ Consolidates widget data into a single value for storage
    Returns json encoded string for questions field """

    val_list = []
    for i, widget in enumerate(self.widgets):
      val_list.append(
          widget.value_from_datadict(data, files, name + '_%s' % i))
    return json.dumps(val_list)


class CreateGPSurvey(ModelForm):

  class Meta:
    model = GPSurvey
    include = ['title', 'created_for', 'questions']
    widgets = {'questions': CreateQuestionsWidget()}


class GivingProjectAdminForm(ModelForm):
  fund_goal = IntegerCommaField(label='Fundraising goal', initial=0,
                                help_text=('Fundraising goal agreed upon by '
                                'the group. If 0, it will not be displayed to '
                                'members and they won\'t see a group progress '
                                'chart for money raised.'))

  class Meta:
    model = GivingProject

