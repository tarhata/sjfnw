from django.shortcuts import redirect
from django.utils.decorators import available_attrs
from functools import wraps
from grants.models import Organization
import logging

def registered_org(function=None):
  def decorator(view_func):

    @wraps(view_func, assigned=available_attrs(view_func))
    def _wrapped_view(request, *args, **kwargs):
      username = request.user.username
      if request.user.is_staff and request.GET.get('user'): #staff override
        username = request.GET.get('user')
        logging.info('Staff override - ' + request.user.username +
                     ' logging in as ' + username)
      try:
        organization = Organization.objects.get(email=username)
        logging.info(organization)
        return view_func(request, organization, *args, **kwargs)
      except Organization.DoesNotExist:
        return redirect('/apply/nr')

    return _wrapped_view

  return decorator
