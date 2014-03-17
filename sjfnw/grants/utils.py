from django.conf import settings
from django.http import HttpResponse, Http404
from django.utils import timezone

from google.appengine.ext import blobstore

import logging, re
logger = logging.getLogger('sjfnw')


def local_date_str(timestamp):
  """ Takes a UTC timestamp and converts to a local date string """

  logger.info(timestamp)
  timestamp = timezone.localtime(timestamp)
  logger.info(timestamp)
  return timestamp.strftime('%m/%d/%Y')

def FindBlobKey(body):
  """ Extract blobkey from request.body """
  if settings.DEBUG: #on dev server, has quotes around it
    key = re.search('blob-key="([^"\s]*)"', body)
  else:
    key = re.search('blob-key=(\S*)', body)
  logger.debug(key)
  if key:
    key = key.group(1)
  else:
    key = None
  logger.info(['Extracted blobkey from request.body: ' + str(key)])
  return key

def FindBlob(file_field, hide_errors=False):
  """Given contents of a file field, return the blob. """

  key = file_field.name.split('/', 1)[0]
  if key:
    blob = blobstore.BlobInfo.get(key)
    if blob:
      logger.info('Found blob - filename ' + blob.filename + ', size ' +
                   str(blob.size) + ', type ' + blob.content_type)
      return blob

  if hide_errors:
    return False
  else:
    raise Http404('Blob not found')

def ServeBlob(application, field_name):
  """Returns file from the Blobstore for serving
    application: GrantApplication or DraftGrantApplication
    field_name: name of the file field """

  #find the filefield
  file_field = getattr(application, field_name)
  if not file_field:
    logger.warning('Unknown file type ' + field_name)
    raise Http404

  blob = FindBlob(file_field)

  response =  HttpResponse(blobstore.BlobReader(blob).read(),
                           content_type=blob.content_type)
  return response

def DeleteBlob(file_field):
  if not file_field:
    logger.info('Delete empty')
    return
  blob = FindBlob(file_field, hide_errors=True)
  if blob:
    blob.delete()
    logger.info('Blob deleted')
    return HttpResponse("deleted")
  else:
    return HttpResponse("nothing deleted")

