from django.conf import settings
from django.http import HttpResponse, Http404
from django.utils import timezone
from google.appengine.ext import blobstore
from sjfnw import constants
import datetime, logging, re

def FindBlob(file_field, both=False):
  """Given contents of a file field, return the blob itself.
  if both==True, return the blobinfo also """
  
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
  
  blob = None
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
        blob = b
        break
      else:
        logging.debug('Creation time matched but filename did not: blobinfo filename was ' + filename + ', found ' + b.filename)
  
  if not blob:
    logging.error('No matching blob found')
    raise Http404
  elif both:
    return binfo, blob
  else:
    return blob

def ServeBlob(application, field_name):
  """Returns file from the Blobstore for serving
    application: GrantApplication or DraftGrantApplication
    field_name: name of the file field """

  #find the filefield
  file_field = getattr(application, field_name)
  if not file_field:
    logging.warning('Unknown file type ' + field_name)
    return Http404
  
  blob = FindBlob(file_field)
  
  response =  HttpResponse(blobstore.BlobReader(blob).read(), content_type=blob.content_type)
  return response      
  
def DeleteBlob(file_field):
  if not file_field:
    logging.info('Delete empty')
    return
  binfo, blob = FindBlob(file_field, both=True)
  binfo.delete()
  blob.delete()
  logging.info('Blob deleted')
  return HttpResponse("deleted")