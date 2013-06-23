import logging
from email.mime.base import MIMEBase

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail import EmailMultiAlternatives

from google.appengine.api import mail as gaemail
from google.appengine.ext import deferred
from google.appengine.runtime import apiproxy_errors

# MODIFIED VERSION OF DJANGOAPPENGINE'S MAIL.PY FILE
# SEE LICENSE AT BOTTOM

def _send_deferred(message, fail_silently=False):
  try:
    message.send()
  except (gaemail.Error, apiproxy_errors.Error):
    if not fail_silently:
      raise


class EmailBackend(BaseEmailBackend):
  """ Asynchronous email backend """

  def send_messages(self, email_messages):
    """ Call _send for each message & return count of messages """

    num_sent = 0
    for message in email_messages:
      if self._send(message):
        num_sent += 1
    return num_sent

  def _copy_message(self, message):
    """ Create and return App Engine EmailMessage class from message """

    gmsg = gaemail.EmailMessage(sender=message.from_email,
                                to=message.to,
                                subject=message.subject,
                                body=message.body)
    if message.extra_headers.get('Reply-To', None):
      gmsg.reply_to = message.extra_headers['Reply-To']
    if message.cc:
      gmsg.cc = list(message.cc)
    if message.bcc:
      gmsg.bcc = list(message.bcc)
    if message.attachments:
      # Must be populated with (filename, filecontents) tuples.
      attachments = []
      for attachment in message.attachments:
        if isinstance(attachment, MIMEBase):
          attachments.append((attachment.get_filename(),
                             attachment.get_payload(decode=True)))
        else:
          attachments.append((attachment[0], attachment[1]))
      gmsg.attachments = attachments
    # Look for HTML alternative content.
    if isinstance(message, EmailMultiAlternatives):
      for content, mimetype in message.alternatives:
        if mimetype == 'text/html':
          gmsg.html = content
          break
    return gmsg

  def _send(self, message):
    """
    Use _copy_message to convert to gae email obj
    Call _defer_message to add to send queue
    """
    try:
      message = self._copy_message(message)
    except (ValueError, gaemail.InvalidEmailError), err:
      logging.error(err)
      if not self.fail_silently:
        raise
      return False
    self._defer_message(message)
    return True

  def _defer_message(self, message):
    queue_name = getattr(settings, 'EMAIL_QUEUE_NAME', 'default')
    deferred.defer(_send_deferred, message, fail_silently=self.fail_silently,
                   _queue=queue_name)

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

