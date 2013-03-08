from django.contrib.auth.models import User
from django.core.validators import MaxLengthValidator
from django.conf import settings
from django.http import HttpResponse, Http404
from django.utils import timezone
from google.appengine.ext import blobstore
from models import GrantApplication, DraftGrantApplication
import datetime, logging, re

def FindBlob(application, file_type):
  """Return file from the Blobstore.

  application: GrantApplication or DraftGrantApplication
  file_type: str indicating which file field """
  
  #find the filefield
  file_field = getattr(application, file_type)
  if not file_field:
    logging.warning('Unknown file type ' + file_type)
    return Http404
  
  #filefield stores key that gets the blobinfo
  blobinfo_key = str(file_field).split('/', 1)[0]
  binfo = blobstore.BlobInfo.get(blobinfo_key)
  #all binfo properties refer to the blobinfo itself, not the blob
  logging.info('Binfo properties: filename ' + binfo.filename + ', size ' + str(binfo.size) + ', type ' + binfo.content_type)
  #reader gets binfo file contents which refer to the actual blob  
  reader = blobstore.BlobReader(binfo) 
    
  #look through the contents for the creation time & filename of the blob
  creation_time, filename = False, False
  for l in reader:
    m = re.match(r"X-AppEngine-Upload-Creation: ([-0-9:. ]+)", l)
    if m:
      creation_time = m.group(1)
      logging.info('Creation time found: ' + str(creation_time))
    m = re.search(r'filename="(.+)"', l)
    if m:
      filename = m.group(1)
      logging.info('Filename found: ' + str(filename))

  if not (creation_time and filename): #error if not found
    logging.error("Couldn't extract creation time and filename - filefield " + str(file_field))
    raise Http404

  if not settings.DEBUG: #convert to datetime for live
    creation_time = datetime.datetime.strptime(creation_time, '%Y-%m-%d %H:%M:%S.%f')
    creation_time = timezone.make_aware(creation_time, timezone.get_current_timezone())
  
  #find blob that matches the creation time
  for b in blobstore.BlobInfo.all():    
    c = b.creation
    if settings.DEBUG: #local - just compare strings
      c = str(timezone.localtime(c))
    else:#live - convert blobstore to datetime
      c = timezone.make_aware(c, timezone.utc)
      c = timezone.localtime(c)
    if c == creation_time:
      logging.debug('Found a creation time match! ' + str(b.filename) + ', ' + str(b.size))
      if b.filename == filename:
        logging.info('Filename matches - returning file')
        response =  HttpResponse(blobstore.BlobReader(b).read(), content_type=b.content_type)
        if b.content_type != 'text/plain' and not '.jpg' in filename.lower():
          response['Content-Disposition'] = 'attachment; filename="' + filename + '"'
        return response
      else:
        logging.debug('Creation time matched but filename did not: blobinfo filename was ' + filename + ', found ' + b.filename)
  logging.error('No matching blob found')
  raise Http404

def GetFileURLs(app):
  """ Given a draft or application
  return a dict of urls for viewing each of its files
  taking into account whether it can be viewed in google doc viewer """
  
  viewer_formats = ('tiff', 'bmp', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'pdf', 'mpeg4', 'mov', 'avi', 'wmv')
  
  #determine whether draft or submitted
  if isinstance(app, GrantApplication):
    logging.info("A submitted app!!!?!?")
    mid_url = 'grants/view-file/'
  elif isinstance(app, DraftGrantApplication):
    logging.info("A draft")
    mid_url = 'grants/draft-file/'
  else:
    logging.error("GetFileURLs received invalid object")
    return {}
  
  #check file fields, compile links
  file_urls = {'budget': '', 'funding_sources':'', 'demographics':'', 'fiscal_letter':'', 'budget1': '', 'budget2': '', 'budget3': '', 'project_budget_file': ''}
  for field in file_urls:
    value = getattr(app, field)
    if value:
      if str(value).lower().split(".")[-1] in viewer_formats: #doc viewer
        file_urls[field] = 'https://docs.google.com/viewer?url='
      file_urls[field] += settings.APP_BASE_URL + mid_url + str(app.pk) + '/' + field
  
  return file_urls
  
def DeleteEmptyFiles(request): #/tools/delete-empty
  """ Delete all 0kb files in the blobstore """
  infos = blobstore.BlobInfo.all().filter('size =', 0)
  count = 0
  for i in infos:
    count += 1
    i.delete()
  logging.info('Deleted ' + str(count) + 'empty files.')
  return HttpResponse("done")

#User username length patch
def patch_user_model(model):
  
  field = model._meta.get_field("username")
  field.max_length = 100
  field.help_text = "Required, 100 characters or fewer. Only letters, numbers, and @, ., +, -, or _ characters."

  # patch model field validator because validator doesn't change if we change max_length
  for v in field.validators:
    if isinstance(v, MaxLengthValidator):
      v.limit_value = 100
  
  # patch admin site forms
  from django.contrib.auth.forms import UserChangeForm, UserCreationForm, AuthenticationForm

  UserChangeForm.base_fields['username'].max_length = 100
  UserChangeForm.base_fields['username'].widget.attrs['maxlength'] = 100
  UserChangeForm.base_fields['username'].validators[0].limit_value = 100
  UserChangeForm.base_fields['username'].help_text = UserChangeForm.base_fields['username'].help_text.replace('30', '100')

  UserCreationForm.base_fields['username'].max_length = 100
  UserCreationForm.base_fields['username'].widget.attrs['maxlength'] = 100
  UserCreationForm.base_fields['username'].validators[0].limit_value = 100
  UserCreationForm.base_fields['username'].help_text = UserChangeForm.base_fields['username'].help_text.replace('30', '100')
  
  AuthenticationForm.base_fields['username'].max_length = 100
  AuthenticationForm.base_fields['username'].widget.attrs['maxlength'] = 100
  AuthenticationForm.base_fields['username'].validators[0].limit_value = 100
  AuthenticationForm.base_fields['username'].help_text = UserChangeForm.base_fields['username'].help_text.replace('30', '100')

if User._meta.get_field("username").max_length != 100:
  patch_user_model(User)