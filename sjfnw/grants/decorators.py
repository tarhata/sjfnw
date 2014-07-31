from django.utils.decorators import available_attrs
from django.shortcuts import redirect

from sjfnw.grants.models import Organization

from functools import wraps
import logging
logger = logging.getLogger('sjfnw')

def registered_org(function=None):
  """ Requires that the logged in user corresponds to an Organization and
      passes that organization as an arg to the view

    Notes:
      - Must be used *after* @login_required
      - If no org is found matching user email, redirects to /apply/nr
      - Works with staff override, indicates in log
  """

  def decorator(view_func):

    @wraps(view_func, assigned=available_attrs(view_func))
    def _wrapped_view(request, *args, **kwargs):
      username = request.user.username
      if request.user.is_staff and request.GET.get('user'): #staff override
        username = request.GET.get('user')
        logger.info('Staff override - ' + request.user.username +
                     ' logging in as ' + username)
      try:
        organization = Organization.objects.get(email=username)
        logger.info(organization)
        return view_func(request, organization, *args, **kwargs)
      except Organization.DoesNotExist:
        return redirect('/apply/nr')

    return _wrapped_view

  return decorator

