import mimetypes
import logging

from django.core.files.base import File
from django.core.files.storage import Storage
from django.core.files.uploadedfile import UploadedFile
from django.core.files.uploadhandler import FileUploadHandler, StopFutureHandlers
from django.utils.encoding import force_unicode

from google.appengine.api import files
from google.appengine.api.images import get_serving_url, NotImageError
from google.appengine.ext.blobstore import BlobInfo, BlobKey, delete, BLOB_KEY_HEADER, BLOB_RANGE_HEADER, BlobReader

from sjfnw.grants.utils import FindBlobKey

logger = logging.getLogger('sjfnw')

# MODIFIED VERSION OF DJANGOAPPENGINES STORAGE FILE
# SEE LICENSE AT BOTTOM

class BlobstoreStorage(Storage):
  """Google App Engine Blobstore storage backend."""

  def _open(self, name, mode='rb'):
    logger.info('storage open ' + str([name]))
    return BlobstoreFile(name, mode, self)

  def _save(self, name, content):
    logger.info('storage _save on ' + str([name]))

    name = name.replace('\\', '/')
    if hasattr(content, 'file') and hasattr(content.file, 'blobstore_info'):
      data = content.file.blobstore_info
    elif hasattr(content, 'blobstore_info'):
      data = content.blobstore_info
    elif isinstance(content, File):
      guessed_type = mimetypes.guess_type(name)[0]
      file_name = files.blobstore.create(mime_type=guessed_type or
                                         'application/octet-stream',
                                         _blobinfo_uploaded_filename=name)

      with files.open(file_name, 'a') as f:
        for chunk in content.chunks():
          f.write(chunk)

      files.finalize(file_name)

      data = files.blobstore.get_blob_key(file_name)

    else:
      raise ValueError("The App Engine storage backend only supports "
                       "BlobstoreFile instances or File instances.")

    if isinstance(data, (BlobInfo, BlobKey)):
      if isinstance(data, BlobInfo):
        logger.info('data is blobinfo, storing its key')
        data = data.key()

      name = name.lstrip('/')
      if len(name) > 65: #shorten it so extension fits in FileField
        name = name.split(".")[0][:60].rstrip() + u'.' + name.split(".")[1]
        logger.info(name)
        logger.info('Returning ' + str(data) + name )
      return '%s/%s' % (data, name)

    else:
      raise ValueError("The App Engine Blobstore only supports BlobInfo "
                       "values. Data can't be uploaded directly. You have to "
                       "use the file upload handler.")

  def delete(self, name):
    delete(self._get_key(name))

  def exists(self, name):
    return self._get_blobinfo(name) is not None

  def size(self, name):
    return self._get_blobinfo(name).size

  def url(self, name):
    try:
      return get_serving_url(self._get_blobinfo(name))
    except NotImageError:
      return None

  def created_time(self, name):
    return self._get_blobinfo(name).creation

  def get_valid_name(self, name):
    return force_unicode(name).strip().replace('\\', '/')

  def get_available_name(self, name):
    return name.replace('\\', '/')

  def _get_key(self, name):
    return BlobKey(name.split('/', 1)[0])

  def _get_blobinfo(self, name):
    return BlobInfo.get(self._get_key(name))

class BlobstoreFile(File):

  def __init__(self, name, mode, storage):
    logger.info('BlobstoreFile__init on ' + name)
    self.name = name
    self._storage = storage
    self._mode = mode
    self.blobstore_info = storage._get_blobinfo(name)

  @property
  def size(self):
    return self.blobstore_info.size

  def write(self, content):
    raise NotImplementedError()

  @property
  def file(self):
    if not hasattr(self, '_file'):
      self._file = BlobReader(self.blobstore_info.key())
    return self._file

class BlobstoreFileUploadHandler(FileUploadHandler):
  """
  File upload handler for the Google App Engine Blobstore.
  """

  def new_file(self, *args, **kwargs):
    """field_name, file_name, content_type, content_length, charset=None"""

    logger.debug('BlobstoreFileUploadHandler.new_file')
    super(BlobstoreFileUploadHandler, self).new_file(*args, **kwargs)

    blobkey = FindBlobKey(self.request.body)
    self.active = blobkey is not None
    if self.active:
      self.blobkey = BlobKey(blobkey)
      raise StopFutureHandlers()

  def receive_data_chunk(self, raw_data, start):
    """
    Add the data to the StringIO file.
    """
    if not self.active:
      return raw_data

  def file_complete(self, file_size):
    """
    Return a file object if we're activated.
    """
    logger.info('BlobstoreFileUploadHandler.file_complete')
    if not self.active:
      logger.info('not active')
      return
    return BlobstoreUploadedFile(
      blobinfo=BlobInfo(self.blobkey),
      charset=self.charset)

class BlobstoreUploadedFile(UploadedFile):
  """
  A file uploaded into memory (i.e. stream-to-memory).
  """

  def __init__(self, blobinfo, charset):
    logger.info('BlobstoreUploadedFile.__init__')
    super(BlobstoreUploadedFile, self).__init__(
      BlobReader(blobinfo.key()), blobinfo.filename,
      blobinfo.content_type, blobinfo.size, charset)
    self.blobstore_info = blobinfo

  def open(self, mode=None):
    pass

  def chunks(self, chunk_size=1024 * 128):
    self.file.seek(0)
    while True:
      content = self.read(chunk_size)
      if not content:
        break
      yield content

  def multiple_chunks(self, chunk_size=1024 * 128):
    return True

#Djangoappengine license:

#Copyright (c) Waldemar Kornewald, Thomas Wanschik, and all contributors.
#All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification,
#are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#
#    2. Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#    3. Neither the name of All Buttons Pressed nor
#       the names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 'AS IS' AND
#ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
#ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

