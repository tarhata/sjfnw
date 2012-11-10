import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

import django.core.signals
from django.core.wsgi import get_wsgi_application
import django.dispatch.dispatcher

def log_exception(*args, **kwds):
    logging.exception('Exception in request:')

#Log errors.
django.dispatch.dispatcher.connect(log_exception, django.core.signals.got_request_exception)

application = get_wsgi_application()