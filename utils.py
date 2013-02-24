from django import forms
from django.core import validators
import logging

class IntegerCommaField(forms.Field):
  """ Allows commas separating thousands
  (Mostly copied from IntegerField) """
  
  default_error_messages = {
    'invalid': u'Enter a number.',
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
    if isinstance(value, (str, unicode)):
      value = value.replace(",", "")
    return super(IntegerCommaField, self).clean(value)