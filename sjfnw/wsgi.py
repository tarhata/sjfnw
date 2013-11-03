from django.core.wsgi import get_wsgi_application
from django.core.signals import got_request_exception
import logging
import os, sys

# set formatting for logging
if os.getenv('SERVER_SOFTWARE', '').startswith('Google App Engine'):
  fr = logging.Formatter(fmt='[%(filename)s:%(lineno)d %(funcName)s]: %(message)s')
else:
  fr = logging.Formatter(fmt='%(levelname)-8s %(asctime)s %(filename)s:%(lineno)d %(funcName)s]: %(message)s')
logging.getLogger().handlers[0].setFormatter(fr)

# path & env vars
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sjfnw.settings")

# log errors
def log_exception(*args, **kwds):
  logging.exception('Exception in request:')
got_request_exception.connect(log_exception)

# define wsgi app
application = get_wsgi_application()

