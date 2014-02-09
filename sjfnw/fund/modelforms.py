from django.forms import ModelForm, widgets

from sjfnw.forms import IntegerCommaField
from sjfnw.fund.models import Donor, Step, GPSurvey, GPSurveyResponse



def custom_integer_field(f, **kwargs):
  if f.verbose_name == '*Amount to ask ($)':
    return IntegerCommaField(**kwargs)
  else:
    return f.formfield()


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

class CreateSurveyWidget(widgets.MultiWidget):

  def __init__(self, attrs=None):
    _widgets = [
      widgets.Select(choices = [n for n in range(1, 10)],)
      widgets.Textarea(), 
      widgets.Textarea(attrs = {'rows': 1}),
      widgets.Textarea(attrs = {'rows': 1}),
      widgets.Textarea(attrs = {'rows': 1}),
      widgets.Textarea(attrs = {'rows': 1}),
      widgets.Textarea(attrs = {'rows': 1}),
      widgets.Textarea(attrs = {'rows': 1})
      for i in range(1, 10)]
    super(CreateSurveyWidget, self).__init__(_widget, attrs)
    

  def decompress(self, value):
    """ Takes single DB value, breaks it up for widget display """
    return []

  def format_output(self, rendered_widgets):
    """ Formats widgets for display.
    Returns HTML """
    return ''

  def value_from_datadict(self, data, files, name):
    """ Consolidates widget data into a single value for storage
    Returns json encoded string for questions field """

class CreateGPSurvey(ModelForm):

  class Meta:
    model = GPSurvey

