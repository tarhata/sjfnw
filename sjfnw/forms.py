from django import forms
from django.core import validators
from django.core.exceptions import ValidationError
import re

class PhoneNumberField(forms.Field):
  default_error_messages = {
    'invalid': u'Enter a 10-digit phone number.',
  }

  def __init__(self, *args, **kwargs):
    super(PhoneNumberField, self).__init__(*args, **kwargs)

  def to_python(self, value):
    """
    Validates that int() can be called on the input.
    Returns '' for empty values.
    """
    value = super(PhoneNumberField, self).to_python(value)
    if value in validators.EMPTY_VALUES:
      return ''
    try:
      int(str(value))
    except (ValueError, TypeError):
      raise ValidationError(self.error_messages['invalid'])
    return value[:3] + u'-' + value[3:6] + u'-' + value[6:]

  def clean(self, value):
    if isinstance(value, (str, unicode)):
      value = re.sub(ur'[()\-\s\u2010]', '', value) #u2010 = hyphen
      if value and len(value) != 10:
        raise ValidationError(self.error_messages['invalid'])
    return super(PhoneNumberField, self).clean(value)

class IntegerCommaField(forms.Field):
  """ Allows commas separating thousands
  (Mostly copied from IntegerField) """

  default_error_messages = {
    'invalid': u'Enter a whole number. (Format: 11009 or 11,009)',
    'max_value': u'Must be less than or equal to %(limit_value)s.',
    'min_value': u'Must be greater than or equal to %(limit_value)s.',
  }

  def __init__(self, max_value=None, min_value=None, *args, **kwargs):
    self.max_value, self.min_value = max_value, min_value
    super(IntegerCommaField, self).__init__(*args, **kwargs)

    if max_value is not None:
      self.validators.append(validators.MaxValueValidator(max_value))
    if min_value is not None:
      self.validators.append(validators.MinValueValidator(min_value))

  def to_python(self, value):
    """
    Validates that int() can be called on the input. Returns the result
    of int(). Returns None for empty values.
    """
    value = super(IntegerCommaField, self).to_python(value)
    if value in validators.EMPTY_VALUES:
      return None
    try:
      value = int(str(value))
    except (ValueError, TypeError):
      raise ValidationError(self.error_messages['invalid'])
    return value

  def clean(self, value):
    """ Process the value prior to to_python
      Removes commas and cents """
    if isinstance(value, (str, unicode)):
      value = value.replace(",", "")
      amount = re.match(r'(\d+)(\.\d{2})?$', value)
      if amount:
        value = amount.group(1)
    return super(IntegerCommaField, self).clean(value)

class GaeLogsForm(forms.Form):
  start = forms.SplitDateTimeField()
  end = forms.SplitDateTimeField()
  version_ids = forms.MultipleChoiceField(choices = [('1', '1'), ('devel', 'devel')])
