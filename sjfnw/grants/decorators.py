from django.shortcuts import redirect
from django.utils.decorators import available_attrs
from functools import wraps
from grants.models import Organization
import logging

def registered_org(function=None):
  def decorator(view_func):
    
    @wraps(view_func, assigned=available_attrs(view_func))
    def _wrapped_view(request, *args, **kwargs):
      try:
        organization = Organization.objects.get(email=request.user.username)
        return view_func(request, organization, *args, **kwargs)
      except Organization.DoesNotExist:
        return redirect('/apply/nr')      
    
    return _wrapped_view
  
  return decorator