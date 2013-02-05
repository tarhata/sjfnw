from django.conf import settings
from django.http import HttpResponse, Http404
from django.utils import timezone
from google.appengine.ext import blobstore
import datetime, logging, re

def FindBlob(application, file_type):
  """Return file from the Blobstore.

  application: GrantApplication or DraftGrantApplication
  file_type: str indicating which file field """
  
  #find the filefield
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
  
  #filefield stores key that gets the blobinfo
  blobinfo_key = str(file_field).split('/', 1)[0]
  binfo = blobstore.BlobInfo.get(blobinfo_key)
  logging.info('Binfo properties: filename ' + binfo.filename + ', size ' + str(binfo.size) + ', type ' + binfo.content_type)
  #all binfo properties refer to the blobinfo itself, not the blob
  #reader gets binfo file contents which refer to the actual blob  
  reader = blobstore.BlobReader(binfo) 
  
  """ example contents:
    Content-Type: application/pdf
    MIME-Version: 1.0
    Content-Length: 7916790
    Content-MD5: OGRkMTkzOGYxZWQ3NjhlMWY4OWNhYjVlMjQ4YWQ1ODc=
    Content-Type: application/pdf
    Content-Disposition: form-data; name="fiscal_letter"; filename="persuasive technology.pdf"
    X-AppEngine-Upload-Creation: 2013-02-04 20:58:26.170000 """
    
  #look through the contents for the creation time & filename of the blob
  creation_time, filename = False, False
  for l in reader:
    logging.info(l)
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
      logging.info('Found a creation time match! ' + str(b.filename) + str(b.content_type) + str(b.size))
      if b.filename == filename:
        logging.info('Filename matches - returning file')
        return HttpResponse(blobstore.BlobReader(b).read(), content_type=b.content_type)
      else:
        logging.warning('Creation time matched but filename did not: blobinfo filename was ' + filename + ', found ' + b.filename)
  logging.warning('No matching blob found')
  raise Http404