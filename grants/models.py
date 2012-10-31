#! /usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
from django.db import models
from django.forms import ModelForm, Textarea
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.validators import MaxLengthValidator

class Grantee(models.Model):
  name = models.CharField(max_length=255)
  email = models.EmailField() #= django username
  
  #org contact info
  address = models.CharField(max_length=100, null=True)
  city = models.CharField(max_length=50, null=True)
  STATE_CHOICES = (
    ('OR', 'OR'),
    ('WA', 'WA'),
    ('ID', 'ID'),
    ('WY', 'WY'),
    ('MT', 'MT'),
  )
  state = models.CharField(max_length=2,choices=STATE_CHOICES, null=True)
  zip = models.CharField(max_length=50, null=True)
  telephone_number = models.CharField(max_length=20, null=True)
  fax_number = models.CharField(max_length=20, null=True, blank=True)
  email_address = models.EmailField(null=True)
  website = models.CharField(max_length=50, null=True, blank=True)
  
  #org info
  STATUS_CHOICES = (
    ('Tribal government', 'Federally recognized American Indian tribal government'),   
    ('501c3', '501(c)3 organization as recognized by the IRS'),
    ('501c4', '501(c)4 organization as recognized by the IRS'),
    ('Sponsored', 'Sponsored by a 501(c)3, 501(c)4, or federally recognized tribal government'),
  )
  status = models.CharField(max_length=50, choices=STATUS_CHOICES, null=True)
  ein = models.CharField(max_length=50, verbose_name="Organization's or Fiscal Sponsor Organization's EIN", null=True)
  founded = models.PositiveIntegerField(verbose_name='Year organization founded', null=True)
  mission_statement = models.TextField(null=True, blank=True)
  
  #fiscal sponsor info (if applicable)
  fiscal_org = models.CharField(verbose_name='Organization name', max_length=255, null=True, blank=True)
  fiscal_person = models.CharField(verbose_name='Contact person', max_length=255, null=True, blank=True)
  fiscal_telephone = models.CharField(verbose_name='Telephone', max_length=25, null=True, blank=True)
  fiscal_email = models.CharField(verbose_name='Email address', max_length=70, null=True, blank=True)
  fiscal_address = models.CharField(verbose_name='Address/City/State/ZIP', max_length=255, null=True, blank=True)
  fiscal_letter = models.FileField(upload_to='uploads/%Y/', null=True,blank=True)
  fiscal_letter_name = models.CharField(max_length=255, null=True,blank=True)
  fiscal_letter_type = models.CharField(max_length=4, null=True,blank=True)
   
  def __unicode__(self):
    return self.name

class OrgProfile(ModelForm):
  class Meta:
    model = Grantee
    exclude = ('name', 'email', 'profile_json')

class GrantCycle(models.Model):
  title = models.CharField(max_length=100)
  open = models.DateTimeField()
  close = models.DateTimeField()
  addition = models.TextField(null=True,blank=True)
  narrative = models.TextField(null=True,blank=True)
  
  def __unicode__(self):
    return self.title
  
  def is_open(self):
    if self.open<timezone.now()<self.close:
      return True
    else:
      return False
  
  def get_status(self):
    today = timezone.now()
    if self.close<today:
      return 'closed'
    elif self.open>today:
      return 'upcoming'
    else:
      return 'open'
  
class SavedGrantApplication(models.Model):
  """ Autosaved draft application """
  organization = models.ForeignKey(Grantee)
  grant_cycle = models.ForeignKey(GrantCycle)
  modified = models.DateTimeField(auto_now=True)
  contents = models.TextField()
  file1 = models.FileField(upload_to='draft/', max_length=255)
  
  def __unicode__(self):
    return self.organization.name + ' saved draft id ' + str(self.pk)

class WordLimitValidator(MaxLengthValidator):
  message = 'Please limit this response to %(limit_value)s words or less.'

class GrantApplication(models.Model):
  """ Submitted grant application """
  
  #automated fields
  submission_time = models.DateTimeField(auto_now_add=True)
  organization = models.ForeignKey(Grantee)
  grant_cycle = models.ForeignKey(GrantCycle)
  
  #contact info
  address = models.CharField(max_length=100)
  city = models.CharField(max_length=50)
  STATE_CHOICES = (
    ('OR', 'OR'),
    ('WA', 'WA'),
    ('ID', 'ID'),
    ('WY', 'WY'),
    ('MT', 'MT'),
  )
  state = models.CharField(max_length=2,choices=STATE_CHOICES)
  zip = models.CharField(max_length=50)
  telephone_number = models.CharField(max_length=20)
  fax_number = models.CharField(max_length=20, null=True, blank=True)
  email_address = models.EmailField()
  website = models.CharField(max_length=50, null=True, blank=True)
  
  #org info
  STATUS_CHOICES = (
    ('Tribal government', 'Federally recognized American Indian tribal government'),   
    ('501c3', '501(c)3 organization as recognized by the IRS'),
    ('501c4', '501(c)4 organization as recognized by the IRS'),
    ('Sponsored', 'Sponsored by a 501(c)3, 501(c)4, or federally recognized tribal government'),
  )
  status = models.CharField(max_length=50, choices=STATUS_CHOICES)
  ein = models.CharField(max_length=50, verbose_name="Organization or Fiscal Sponsor EIN")
  founded = models.PositiveIntegerField(verbose_name='Year founded')
  mission = models.TextField(verbose_name="Mission statement:")
  
  #grant & financial info
  contact_person = models.CharField(max_length=250, verbose_name='Contact person for this grant application (name and title)')
  amount_requested = models.PositiveIntegerField(verbose_name='Amount requested $')
  SUPPORT_CHOICES = (
    ('General support', 'General support'),   
    ('Project support', 'Project support'),
  )
  support_type = models.CharField(max_length=50, choices=SUPPORT_CHOICES)
  grant_period = models.CharField(max_length=250)
  start_year = models.CharField(max_length=250,verbose_name='Start date of fiscal year')
  budget_last = models.PositiveIntegerField(verbose_name='Org. budget last fiscal year')
  budget_current = models.PositiveIntegerField(verbose_name='Org. budget this fiscal year')
  project_title = models.CharField(max_length=250,verbose_name='Project title (if applicable)', null=True, blank=True)
  project_budget = models.PositiveIntegerField(verbose_name='Project budget (if applicable)', null=True, blank=True)
  grant_request = models.TextField(verbose_name="Summarize the grant request:")
  previous_grants = models.CharField(max_length=255, verbose_name="Previous SJF grants awarded (amounts and year)")
  
  #fiscal sponsor
  fiscal_org = models.CharField(verbose_name='Fiscal org. name', max_length=255, null=True, blank=True)
  fiscal_person = models.CharField(verbose_name='Contact person', max_length=255, null=True, blank=True)
  fiscal_telephone = models.CharField(verbose_name='Telephone', max_length=25, null=True, blank=True)
  fiscal_email = models.CharField(verbose_name='Email address', max_length=70, null=True, blank=True)
  fiscal_address = models.CharField(verbose_name='Address/City/State/ZIP', max_length=255, null=True, blank=True)
  
  #narrative
  narrative1 = models.TextField(validators=[WordLimitValidator(1800)], verbose_name="Describe your organization's mission, history and major accomplishments.")
  narrative2 = models.TextField(validators=[WordLimitValidator(900)], verbose_name='Social Justice Fund prioritizes groups that are led by the people most impacted by the issues the group is working on, and continually build leadership from within their own communities.<ol type="a"><li>Who are the communities most directly impacted by the issues your organization addresses?</li><li>How are those communities involved in the leadership of your organization, and how does your organization remain accountable to those communities?</li></ol>')
  narrative3 = models.TextField(validators=[WordLimitValidator(2700)], verbose_name='Social Justice Fund prioritizes groups that understand and address the underlying, or root causes of the issues, and that bring people together to build collective power.<ol type="a"><li>What problems, needs or issues does your work address?</li><li>What are the root causes of these issues</li><li>How does your organization build collective power?</li><li>How will your work change the root causes and underlying power dynamics of the identified problems, needs or issues?</li></ol>')
  narrative4 = models.TextField(validators=[WordLimitValidator(1800)], verbose_name='Social Justice Fund prioritizes groups that see themselves as part of a larger movement for social change, and work towards strengthening that movement.<ol type="a"><li>Describe at least two coalitions, collaborations, partnerships or networks that you participate in as an approach to social change.</li><li>What are the purposes and impacts of these collaborations?</li><li>What is your organizations role in these collaborations?</li><li>If your collaborations cross issue or constituency lines, how will this will help build a broad, unified, and effective progressive movement?</li><li>Provide <u>names and contact information</u> for two people who are familiar with your organizations role in these collaborations so we can contact them for more information.</li></ol>') #5 in doc --end of retyped
  narrative5 = models.TextField(validators=[WordLimitValidator(1800)], verbose_name="<b>Describe how your work promotes diversity and addresses inequality, oppression and discrimination, both in your organization and in the larger society.</b>  Social Justice Fund prioritizes groups working on racial justice, especially those making connections between racism, economic injustice, homophobia, and other forms of oppression.  If you are a primarily white-led organization, also describe how you work as an ally to communities of color. Be as specific as possible, and list at least one organization led by people of color that we can contact as a reference for your racial justice work. While we believe people of color must lead the struggle for racial justice, we also realize that the demographics of our region make the work of white anti-racist allies critical to winning racial justice.")
  narrative6 = models.TextField(null=True, blank=True)
  
  #files
  file1 = models.FileField(upload_to='up/', max_length=255)

  fiscal_letter = models.FileField(upload_to='uploads/%Y/', null=True,blank=True)
  fiscal_letter_name = models.CharField(max_length=255, null=True,blank=True)
  fiscal_letter_type = models.CharField(max_length=4, null=True,blank=True)
  
  #admin fields  
  SCREENING_CHOICES = (
    (10, 'Received'),
    (20, 'Incomplete'),
    (30, 'Complete'),
    (40, 'Proposal Denied'),
    (50, 'Proposal Accepted'), #cutoff for gp view
    (60, 'Grant Denied'),  
    (70, 'Grant Issued'),
    (80, 'Grant Paid'),
    (90, 'Closed'),
  )
  screening_status = models.IntegerField(choices=SCREENING_CHOICES, default=10, blank = True, null=True)
  scoring_bonus_poc = models.BooleanField(default=False, verbose_name='Scoring bonus for POC-led?')
  scoring_bonus_geo = models.BooleanField(default=False, verbose_name='Scoring bonus for geographic diversity?')
  
  def __unicode__(self):
    return unicode(self.organization)

class GrantApplicationForm(ModelForm):
  class Meta:
    model = GrantApplication
    widgets = {
          'mission': Textarea(attrs={'rows': 3, 'onKeyUp':'charLimitDisplay(this, 300)'}),
          'grant_request': Textarea(attrs={'rows': 3}),
          'narrative1': Textarea(attrs={'onKeyUp':'charLimitDisplay(this, 1800)'}),
          'narrative2': Textarea(attrs={'onKeyUp':'charLimitDisplay(this, 900)'}),
          'narrative3': Textarea(attrs={'onKeyUp':'charLimitDisplay(this, 2700)'}),
          'narrative4': Textarea(attrs={'onKeyUp':'charLimitDisplay(this, 1800)'}),
          'narrative5': Textarea(attrs={'onKeyUp':'charLimitDisplay(this, 1800)'}),
          'narrative6': Textarea(attrs={'onKeyUp':'charLimitDisplay(this, 2700)'}),
        }
    
class NarrativeText(models.Model):
  name = models.CharField(max_length=100, default="Application", unique=True)
  narrative_heading = models.TextField(null=True, blank=True)
  narrative1 = models.TextField(null=True, blank=True)
  narrative2 = models.TextField(null=True, blank=True)
  narrative3 = models.TextField(null=True, blank=True)
  narrative4 = models.TextField(null=True, blank=True)
  narrative5 = models.TextField(null=True, blank=True)
