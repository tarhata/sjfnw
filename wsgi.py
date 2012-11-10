import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

import logging
import django.core.signals
from django.core.wsgi import get_wsgi_application
from django.core.signals import got_request_exception

def log_exception(*args, **kwds):
  logging.exception('Exception in request:')

# Log errors.
got_request_exception.connect(log_exception)

application = get_wsgi_application()