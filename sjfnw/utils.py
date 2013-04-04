from django.contrib.auth.models import User
from django.core.validators import MaxLengthValidator
import logging

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