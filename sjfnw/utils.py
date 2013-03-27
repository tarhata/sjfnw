from django import forms
from django.contrib.auth.models import User
from django.core import validators
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
import logging, re

class PhoneNumberField(forms.Field):
  default_error_messages = {
    'invalid': u'Enter a 10-digit phone number.',
  }
  
  def __init__(self, *args, **kwargs):
    super(PhoneNumberField, self).__init__(*args, **kwargs)
  
  def to_python(self, value):
    """
    Validates that int() can be called on the input. Returns the ---
    . Returns '' for empty values.
    """
    value = super(PhoneNumberField, self).to_python(value)
    if value in validators.EMPTY_VALUES:
      return ''
    try:
      int(str(value))
    except (ValueError, TypeError):
      raise ValidationError(self.error_messages['invalid'])
    return value[:3] + '-' + value[3:6] + '-' + value[6:]
  
  def clean(self, value):
    if isinstance(value, (str, unicode)):
      value = re.sub('[()\-\s]', '', str(value))
      if value and len(value) != 10:
        raise ValidationError(self.error_messages['invalid'])
    return super(PhoneNumberField, self).clean(value)
    
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

class GaeLogsForm(forms.Form):
  start = forms.SplitDateTimeField()
  end = forms.SplitDateTimeField()
  version_ids = forms.MultipleChoiceField(choices = [('1', '1'), ('devel', 'devel')])
  
#User username length patch
def patch_user_model(model):
  
  field = model._meta.get_field("username")
  field.max_length = 100
  field.help_text = "Required, 100 characters or fewer. Only letters, numbers, and @, ., +, -, or _ characters."

  # patch model field validator because validator doesn't change if we change max_length
  for v in field.validators:
    if isinstance(v, MaxLengthValidator):
      v.limit_value = 100
  
  # patch admin site forms
  from django.contrib.auth.forms import UserChangeForm, UserCreationForm, AuthenticationForm

  UserChangeForm.base_fields['username'].max_length = 100
  UserChangeForm.base_fields['username'].widget.attrs['maxlength'] = 100
  UserChangeForm.base_fields['username'].validators[0].limit_value = 100
  UserChangeForm.base_fields['username'].help_text = UserChangeForm.base_fields['username'].help_text.replace('30', '100')

  UserCreationForm.base_fields['username'].max_length = 100
  UserCreationForm.base_fields['username'].widget.attrs['maxlength'] = 100
  UserCreationForm.base_fields['username'].validators[0].limit_value = 100
  UserCreationForm.base_fields['username'].help_text = UserChangeForm.base_fields['username'].help_text.replace('30', '100')
  
  AuthenticationForm.base_fields['username'].max_length = 100
  AuthenticationForm.base_fields['username'].widget.attrs['maxlength'] = 100
  AuthenticationForm.base_fields['username'].validators[0].limit_value = 100
  AuthenticationForm.base_fields['username'].help_text = UserChangeForm.base_fields['username'].help_text.replace('30', '100')

if User._meta.get_field("username").max_length != 100:
  patch_user_model(User)