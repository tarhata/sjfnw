from functools import wraps
from django.shortcuts import redirect
from django.utils.decorators import available_attrs
import logging

def approved_membership(function=None):
  def decorator(view_func):
    @wraps(view_func, assigned=available_attrs(view_func))
    def _wrapped_view(request, *args, **kwargs):
      if request.membership_status == 3: #success, just do the view func
        return view_func(request, *args, **kwargs)
      elif request.membership_status == 2: #membership(s) not approved
        logging.info('Membership(s) not approved, redirecting to pending')
        return redirect('/fund/pending')
      elif request.membership_status == 1: #no memberships
        logging.info('No memberships, redirecting to projects page')
        return redirect('/fund/projects')
      else: #no member object
        return redirect('/fund/not-member')

    return _wrapped_view
  return decorator
