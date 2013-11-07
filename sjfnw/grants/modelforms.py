from django import forms
from django.forms import ValidationError, ModelForm

from sjfnw.grants.models import GrantApplication, DraftGrantApplication

import logging
logger = logging.getLogger('sjfnw')


class AppAdminForm(ModelForm):
  def clean(self):
    cleaned_data = super(AppAdminForm, self).clean()
    status = cleaned_data.get("screening_status")
    if status >= 100:
      logger.info('Require check details')
    return cleaned_data

  class Meta:
    model = GrantApplication

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


