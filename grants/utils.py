from django.conf import settings
from django.http import HttpResponse, Http404
from django.utils import timezone
from google.appengine.ext import blobstore
import datetime, logging

def FindBlob(application, file_type):
  """Return file from the Blobstore.

  application: GrantApplication or DraftGrantApplication
  file_type: str indicating which file field """
  
  #find the file
  if file_type == 'budget':
    file_field = application.budget
  elif file_type == 'demographics':
    file_field = application.demographics
  elif file_type == 'funding':
    file_field = application.funding_sources
  elif file_type == 'fiscal_letter':
    file_field = application.fiscal_letter
  else:
    logging.warning('Unknown file type ' + file_type)
    return Http404
  
  #filefield stores key that gets us the blobinfo
  blobinfo_key = str(file_field).split('/', 1)[0]
  logging.info('Info key: ' + blobinfo_key)
  binfo = blobstore.BlobInfo.get(blobinfo_key)
  #all binfo properties refer to the blobinfo itself, not the blob  
  reader = blobstore.BlobReader(binfo) #reads the info file contents which refer to the actual blob
  
  """ example contents:
    Content-Type: application/pdf
    MIME-Version: 1.0
    Content-Length: 7916790
    Content-MD5: OGRkMTkzOGYxZWQ3NjhlMWY4OWNhYjVlMjQ4YWQ1ODc=
    Content-Type: application/pdf
    Content-Disposition: form-data; name="fiscal_letter"; filename="persuasive technology.pdf"
    X-AppEngine-Upload-Creation: 2013-02-04 20:58:26.170000 """
    
  #look through the info for the creation time of the blob
  logging.info(str(reader))
  blobinfo_dict =  dict([l.strip().split(': ', 1) for l in reader if l.strip()])
  creation_time = blobinfo_dict['X-AppEngine-Upload-Creation']
  content_disp = blobinfo_dict['Content-Disposition']
  logging.info('Blob dict: ' + str(blobinfo_dict))
  
  if not settings.DEBUG: #convert to datetime for live
    creation_time = datetime.datetime.strptime(creation_time, '%Y-%m-%d %H:%M:%S.%f')
    creation_time = timezone.make_aware(creation_time, timezone.get_current_timezone())
  
  logging.info('Looking for: ' + str(creation_time))
  
  #find blob that matches the creation time
  
  response = False
  for b in  blobstore.BlobInfo.all():    
    c = b.creation
    if settings.DEBUG: #local - just compare strings
      if str(timezone.localtime(c)) == creation_time:
        return HttpResponse(blobstore.BlobReader(b).read(), content_type=b.content_type)
    else:
      c = timezone.make_aware(c, timezone.utc)
      if timezone.localtime(c) == creation_time:
        logging.info('Found a match! ' + str(b.filename) + str(b.content_type))
        return HttpResponse(blobstore.BlobReader(b).read(), content_type=b.content_type)
  logging.warning('No blob matching the creation time')
  return Http404