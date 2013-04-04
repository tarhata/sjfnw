from django.conf import settings
from django.http import HttpResponse, Http404
from django.utils import timezone
from google.appengine.ext import blobstore
import datetime, logging, re

def FindBlobKey(body):
  """ Extract blobkey from request.body """
  if settings.DEBUG: #on dev server, has quotes around it
    key = re.search('blob-key="(.*)"', body)
  else:
    key = re.search('blob-key=(\S*)', body)
  if key:
    key = key.group(1)
  else:
    key = None
  logging.info(['FindBlobKey gets ' + str(key)])
  return key
  
def FindBlob(file_field):
  """Given contents of a file field, return the blob. """
  
  key = file_field.name.split('/', 1)[0]
  if key:
    blob = blobstore.BlobInfo.get(key)
    if blob:
      logging.info('Found blob - filename ' + blob.filename + ', size ' + str(blob.size) + ', type ' + blob.content_type)
      return blob

  raise Http404('Blob not found')

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
  blob = FindBlob(file_field)
  blob.delete()
  logging.info('Blob deleted')
  return HttpResponse("deleted")