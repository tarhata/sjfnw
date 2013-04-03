import os, sys,logging

WSGI_APPLICATION = 'sjfnw.wsgi.application'

SECRET_KEY = '*r-$b*8hglm+959&7x043hlm6-&6-3d3vfc4((7yd0dbrakhvi'

if (os.getenv('SERVER_SOFTWARE', '').startswith('Google App Engine') or os.getenv('SETTINGS_MODE') == 'prod'):
  DATABASES = {
    'default': {
      'ENGINE': 'google.appengine.ext.django.backends.rdbms',
      'INSTANCE': 'sjf-northwest:sjf',
      'NAME': 'sjfdb',
    }
  }
  DEBUG = False
  APP_BASE_URL = 'http://sjf-nw.appspot.com/' #until i learn how to do this
else:
  DATABASES = {
    'default': {
      'ENGINE': 'django.db.backends.mysql',
      'USER': 'root',
      'PASSWORD': 'SJFdb',
      'HOST': 'localhost',
      'NAME': 'sjfdb',
    }
  }
  DEBUG = True
  APP_BASE_URL = 'http://localhost:8080/'

INSTALLED_APPS = (
  'django.contrib.auth',
  'django.contrib.admin',
  'django.contrib.contenttypes',
  'django.contrib.humanize',
  'django.contrib.sessions',
  'django.contrib.messages',
  'sjfnw.grants',
  'sjfnw.fund',
  'sjfnw.scoring',
  'pytz',
  'djangoappengine', # last so it can override a few manage.py commands
)

MIDDLEWARE_CLASSES = (
  'google.appengine.ext.appstats.recording.AppStatsDjangoMiddleware', #must be first
  'django.middleware.common.CommonMiddleware',
  'django.contrib.sessions.middleware.SessionMiddleware',
  'django.contrib.auth.middleware.AuthenticationMiddleware',
  'django.contrib.messages.middleware.MessageMiddleware',
  'sjfnw.fund.middleware.MembershipMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
  'django.contrib.auth.context_processors.auth',
  'django.core.context_processors.request', #only used in fund/base.html js
  #'django.contrib.messages.context_processors.messages', messages var. not using yet
)
TEMPLATE_DIRS = (os.path.join(os.path.dirname(__file__), 'templates'),)

STATIC_URL = '/static/'

ROOT_URLCONF = 'sjfnw.urls'
APPEND_SLASH = False

LOGGING = {'version': 1,}

#djangoappengine email settings
EMAIL_BACKEND = 'djangoappengine.mail.AsyncEmailBackend'
EMAIL_QUEUE_NAME = 'default'

USE_TZ = True
TIME_ZONE = 'America/Los_Angeles'

DEFAULT_FILE_STORAGE = 'djangoappengine.storage.BlobstoreStorage'
SERVE_FILE_BACKEND = 'djangoappengine.storage.serve_file'
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024

FILE_UPLOAD_HANDLERS = (
    #'grants.views.AppUploadHandler', #custom attempt
    'djangoappengine.storage.BlobstoreFileUploadHandler',
    #'django.core.files.uploadhandler.MemoryFileUploadHandler',
  )
