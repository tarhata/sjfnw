from django.core.wsgi import get_wsgi_application
from django.core.signals import got_request_exception
import logging
import os, sys

sys.path.append(os.path.dirname(__file__))
#logging.info(os.path.dirname(__file__))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sjfnw.settings")

# Log errors.
def log_exception(*args, **kwds):
  logging.exception('Exception in request:')
got_request_exception.connect(log_exception)

application = get_wsgi_application()