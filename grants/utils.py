from django.conf import settings
from django.http import HttpResponse, Http404
from django.utils import timezone
from google.appengine.ext import blobstore
import datetime, logging

def FindBlob(application, file_type):
  """Return file from the Blobstore.  Args:
  application = GrantApplication or DraftGrantApplication object
  file_type: str indicating which file field """
  
  #find the file
  if file_type == 'budget':
    file_field = application.budget
  elif file_type == 'demographics':
    file_field = application.demographics
  elif file_type == 'funding':
    file_field = application.funding_sources
  else:
    logging.warning('Unknown file type ' + file_type)
    return Http404
  
  #filefield stores key that gets us the blobinfo
  blobinfo_key = str(file_field).split('/', 1)[0]
  logging.info('Info key: ' + blobinfo_key)
  binfo = blobstore.BlobInfo.get(blobinfo_key)
  logging.info('Blob creation: ' + str(binfo.creation))
  logging.info('Blob content type: ' + str(binfo.content_type))
  return HttpResponse(blobstore.BlobReader(binfo).read(), content_type=binfo.content_type)
  
  """
  for l in blobinfo:
    print(l)
  #look through the info for the creation time of the blob
  blobinfo_dict =  dict([l.split(': ', 1) for l in blobinfo if l.strip()])
  creation_time = blobinfo_dict['X-AppEngine-Upload-Creation'].strip()
  #Content-Disposition: form-data; name=file1; filename="ODO.jpg"
  
  if not settings.DEBUG: #convert to datetime for live
    creation_time = datetime.datetime.strptime(creation_time, '%Y-%m-%d %H:%M:%S.%f')
    creation_time = timezone.make_aware(creation_time, timezone.get_current_timezone())
  
  logging.info('Looking for: ' + str(creation_time))
  
  #find blob that matches the creation time
  for b in  blobstore.BlobInfo.all():    
    c = b.creation
    if settings.DEBUG: #local - just compare strings
      if str(timezone.localtime(c)) == creation_time:
        return HttpResponse(blobstore.BlobReader(b).read(), content_type=b.content_type)
    else:
      c = timezone.make_aware(c, timezone.utc)
      if timezone.localtime(c) == creation_time:
        return HttpResponse(blobstore.BlobReader(b).read(), content_type=b.content_type)
  logging.warning('No blob matching the creation time')
  return Http404 """