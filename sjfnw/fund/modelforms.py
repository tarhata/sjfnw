from django.db import models
from django.forms import ModelForm, widgets, ValidationError
from django.utils import timezone

from sjfnw.forms import IntegerCommaField
from sjfnw.fund.models import Donor, Step, Survey, GPSurvey, GivingProject, SurveyResponse

import json

import logging
logger = logging.getLogger('sjfnw')



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


class DonorForm(ModelForm):
  """ used to edit a contact (creation uses custom form) """

  formfield_callback = custom_integer_field

  class Meta:
    model = Donor
    fields = ('firstname', 'lastname', 'amount', 'likelihood', 'phone',
              'email', 'notes')
    widgets = {'notes': widgets.Textarea(attrs={'cols': 25, 'rows': 4})}


class DonorPreForm(ModelForm):
  """ For editing a contact prior to fund training """

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
    for i in range(1, 6):
      _widgets += [widgets.Textarea(attrs = {'rows': 2}),
                   widgets.Textarea(attrs = {'rows': 1, 'class': 'survey-choice'}),
                   widgets.Textarea(attrs = {'rows': 1, 'class': 'survey-choice'}),
                   widgets.Textarea(attrs = {'rows': 1, 'class': 'survey-choice'}),
                   widgets.Textarea(attrs = {'rows': 1, 'class': 'survey-choice'}),
                   widgets.Textarea(attrs = {'rows': 1, 'class': 'survey-choice'})]
    super(CreateQuestionsWidget, self).__init__(_widgets, attrs)


  def decompress(self, value):
    """ Takes single DB value, breaks it up for widget display """
    val_list = []
    if value:
      dic = json.loads(value)
      for q in dic:
        val_list.append(q['question'])
        count = 1
        for choice in q['choices']:
          val_list.append(choice)
          count += 1
        for i in range(count, 6):
          val_list.append(None)
      return val_list
    else:
      return []

  def format_output(self, rendered_widgets):
    """ Formats widgets for display.
    Returns HTML """
    html = ('<table id="survey-questions">'
            '<tr><th></th><th>Title</th><th>Choices</th></tr>')
    for i in range(0, len(rendered_widgets), 6):
      html += ('<tr><td>' + str((i+6)/6) + '</td><td>' +
              rendered_widgets[i] + '</td><td>' + rendered_widgets[i+1] +
              rendered_widgets[i+2] + rendered_widgets[i+3] +
              rendered_widgets[i+4] + rendered_widgets[i+5] + '</td></tr>')
    html += '</table>'
    return html


  def value_from_datadict(self, data, files, name):
    """ Consolidates widget data into a single value for storage
    Returns json encoded string for questions field
    [{'question': 'Rate the session', 'options': ['1', '2', '3', '4', '5']}]"""
    #logger.info('value_from_datadict, data: ' + str(data))

    value = []
    for i in range(0, len(self.widgets), 6):
      val = self.widgets[i].value_from_datadict(data, files, name + '_%s' % i)
      if val:
        dic = {'question': val, 'choices': []}
        for c in range(1, 6):
          w = i+c
          val = self.widgets[w].value_from_datadict(data, files, name + '_%s' % w)
          if val:
            dic['choices'].append(val)
          else: #blank choice
            break
        value.append(dic)
      else: #blank question
        break

    #logger.info('Returning ' + json.dumps(value))
    return json.dumps(value)



class CreateSurvey(ModelForm):

  class Meta:
    model = Survey
    include = ['title', 'created_for', 'questions']
    widgets = {'questions': CreateQuestionsWidget()}

  def clean_questions(self):
    questions = self.cleaned_data['questions']
    if questions == '[]':
      raise ValidationError('Enter at least one question')
    return questions


class DisplayQuestionsWidget(widgets.MultiWidget):
  """ Displays a Survey's questions to GP members """

  def __init__(self, survey, attrs=None):
    #logger.info('DisplayQuestionsWidget __init__')
    self.questions = json.loads(survey.questions)
    _widgets = []
    for question in self.questions:
      if question['choices']:
        _widgets.append(widgets.RadioSelect(choices =
            [(choice, choice) for i, choice in enumerate(question['choices'])]))
      else:
        _widgets.append(widgets.Textarea(attrs={'class':'survey-text'}))

    super(DisplayQuestionsWidget, self).__init__(_widgets, attrs)


  def decompress(self, value):
    """ Takes single DB value, breaks it up for widget display """
    #logger.info('DisplayQuestionsWidget decompress' + str(value))
    if value:
      val_list = json.loads(value)
      return_list = []
      for i in range(1, len(val_list), 2):
        return_list.append(val_list[i])
      return return_list
    else:
      return [None for widget in self.widgets]

  def format_output(self, rendered_widgets):
    """ Formats widgets for display.
    Returns HTML """
    html = '<table id="survey-questions">'
    i = 0
    for q in self.questions:
      html += ('<tr><th>' + str(i+1) + '.</th><td>' + q['question'] + 
               rendered_widgets[i] + '</td></tr>')
      i += 1
    html += '</table>'
    return html


  def value_from_datadict(self, data, files, name):
    """ Consolidates widget data into a single value for storage
    Returns json encoded string for questions field """

    val_list = []
    for i, widget in enumerate(self.widgets):
      val_list.append(self.questions[i]['question'])
      val_list.append(widget.value_from_datadict(data, files, name + '_%s' % i))
    return json.dumps(val_list)

class SurveyResponseForm(ModelForm):

  class Meta:
    model = SurveyResponse
    widgets = {'date': widgets.HiddenInput(),
               'gp_survey': widgets.HiddenInput() }

  def __init__(self, survey, *args, **kwargs):
    #logger.info('SurveyResponseForm __init__')
    super(SurveyResponseForm, self).__init__(*args, **kwargs)
    self.fields['responses'].widget = DisplayQuestionsWidget(survey)

  def clean_responses(self):
    data = json.loads(self.cleaned_data['responses'])
    for response in data:
      if response is None or response == '':
        raise ValidationError('Please answer every question.')
    return self.cleaned_data['responses']

class GivingProjectAdminForm(ModelForm):
  fund_goal = IntegerCommaField(label='Fundraising goal', initial=0,
                                help_text=('Fundraising goal agreed upon by '
                                'the group. If 0, it will not be displayed to '
                                'members and they won\'t see a group progress '
                                'chart for money raised.'))

  class Meta:
    model = GivingProject

