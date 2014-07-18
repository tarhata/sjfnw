from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from sjfnw import constants

import logging
logger = logging.getLogger('sjfnw')

def NotifyApproval(membership):
  subject, from_email = 'Membership Approved', constants.FUND_EMAIL
  to = membership.member.email
  html_content = render_to_string('fund/email_account_approved.html',
                                  {'login_url':constants.APP_BASE_URL + 'fund/login',
                                   'project':membership.giving_project})
  text_content = strip_tags(html_content)
  msg = EmailMultiAlternatives(subject, text_content, from_email, [to],
                               ['sjfnwads@gmail.com']) #bcc for testing
  msg.attach_alternative(html_content, "text/html")
  msg.send()
  logger.info('Approval email sent to ' + unicode(membership) + ' at ' + to)

