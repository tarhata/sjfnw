import os

WSGI_APPLICATION = 'wsgi.application'

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
  'django.contrib.admin',
  'django.contrib.contenttypes',
  'django.contrib.auth',
  'django.contrib.sessions',
  'django.contrib.messages',
  'grants',
  'fund',
  'scoring',
  'djangoappengine', # last so it can override a few manage.py commands
)

MIDDLEWARE_CLASSES = (
  'google.appengine.ext.appstats.recording.AppStatsDjangoMiddleware', #must be first
  'django.middleware.common.CommonMiddleware',
  'django.contrib.sessions.middleware.SessionMiddleware',
  'django.contrib.auth.middleware.AuthenticationMiddleware',
  'django.contrib.messages.middleware.MessageMiddleware',
  'fund.middleware.MembershipMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
  'django.contrib.auth.context_processors.auth',
  'django.core.context_processors.request',
  'django.core.context_processors.media',
  'django.contrib.messages.context_processors.messages',
)

TEMPLATE_DIRS = (os.path.join(os.path.dirname(__file__), 'templates'),)

ROOT_URLCONF = 'urls'
APPEND_SLASH = False

LOGGING = {
  'version': 1,
}

#djangoappengine email settings
EMAIL_BACKEND = 'djangoappengine.mail.AsyncEmailBackend'
EMAIL_QUEUE_NAME = 'default'

STATIC_URL = '/static/'

USE_TZ = True
TIME_ZONE = 'America/Los_Angeles'

#settings to try to make error reporting happen
SERVER_EMAIL = 'sjfnwads@gmail.com'
DEFAULT_FROM_EMAIL = 'sjfnwads@gmail.com'
ADMINS = (('Aisa', 'sjfnwads@gmail.com'),)

PREPARE_UPLOAD_BACKEND = 'djangoappengine.storage.prepare_upload'
DEFAULT_FILE_STORAGE = 'djangoappengine.storage.BlobstoreStorage'
SERVE_FILE_BACKEND = 'djangoappengine.storage.serve_file'
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024

FILE_UPLOAD_HANDLERS = (
    #'grants.views.AppUploadHandler', #custom attempt
    'djangoappengine.storage.BlobstoreFileUploadHandler',
    'django.core.files.uploadhandler.MemoryFileUploadHandler',
  ) 

### CUSTOM SETTINGS

APP_SUPPORT_EMAIL = 'webmaster@socialjusticefund.org' #just email
APP_SEND_EMAIL = 'sjfnwads@gmail.com' #can include name is_email_valid(email_address)
SUPPORT_FORM_URL = 'https://docs.google.com/spreadsheet/viewform?formkey=dHZ2cllsc044U2dDQkx1b2s4TExzWUE6MQ'
