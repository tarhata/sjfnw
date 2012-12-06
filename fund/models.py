from django import forms
from django.db import models
from django.forms import ModelForm
import datetime
from grants.models import GrantCycle
from django.utils import timezone
from django.core.validators import MaxValueValidator
 
class GivingProject(models.Model):
  title = models.CharField(max_length=255)
  public = models.BooleanField(default=True)
  
  #fundraising
  fundraising_deadline = models.DateField(help_text='Members will stop receiving reminder emails at this date.')
  fund_goal = models.PositiveIntegerField(default=0)
  pre_approved = models.TextField(null=True, blank=True, help_text='List of member emails, separated by commas.  Anyone who registers using an email on this list will have their account automatically approved.  Emails are removed from the list once they have registered.  IMPORTANT: Any syntax error can make this feature stop working; in that case memberships will default to requiring manual approval by an administrator.') #remove null from all char
  suggested_steps = models.TextField(default='Talk to about project\nInvite to SJF event\nSet up time to meet for the ask\nAsk\nFollow up\nThank', help_text='Displayed to users when they add a step.  Put each step on a new line')
  
  calendar = models.CharField(max_length=255, null=True, blank=True, help_text= 'Calendar ID of a google calendar (not the whole embed text)')
  resources = models.ManyToManyField('Resource', through = 'ProjectResource', null=True, blank=True)

  def __unicode__(self):
    return self.title+' '+unicode(self.fundraising_deadline.year)
    
class Member(models.Model):
  email = models.CharField(max_length=255)
  first_name = models.CharField(max_length=100)
  last_name = models.CharField(max_length=100)
  
  giving_project = models.ManyToManyField(GivingProject, through='Membership')
  current = models.IntegerField(default=0)
  
  def __unicode__(self):
    return unicode(self.first_name +' '+self.last_name)
    
class Membership(models.Model): #relationship b/n member and gp
  giving_project = models.ForeignKey(GivingProject)
  member = models.ForeignKey(Member)
  approved = models.BooleanField(default=False)
  leader = models.BooleanField(default=False)
  
  emailed = models.DateField(default='2000-01-01', help_text='Last time this member was sent an overdue steps reminder')
  last_activity = models.DateField(default='2000-01-01', help_text='Last activity by this user on this membership.')
  
  notifications = models.TextField(default='', blank=True)
  
  def __unicode__(self):
    return unicode(self.member)+u', '+unicode(self.giving_project)
    
  def has_overdue(self): #remove
    donors = self.donor_set.all()
    overdue = 0
    day = datetime.timedelta(days=1)
    for donor in donors:
      if donor.has_overdue() and donor.has_overdue()>day: #1 day grace period to member to update
        overdue = overdue+1
    return overdue

  def asked(self): #remove
    return self.donor_set.filter(asked=True).count()
        
  def pledged(self): #remove
    donors = self.donor_set.all()
    amt = 0
    for donor in donors:
      if donor.pledged:
        amt = amt + donor.pledged
    return amt
  
  def gifted(self): #remove
    donors = self.donor_set.all()
    amt = 0
    for donor in donors:
      amt = amt + donor.gifted
    return amt

  def estimated(self): #remove
    estimated = 0
    donors = self.donor_set.all()
    for donor in donors:
      estimated = estimated + donor.amount*donor.likelihood/100
    return estimated

class Donor(models.Model):
  membership = models.ForeignKey(Membership)
  
  firstname = models.CharField(max_length=100, verbose_name='*First name')
  lastname = models.CharField(max_length=100, null=True, blank=True, verbose_name='Last name')
  PRIVACY_CHOICES = (
    ('PR', 'Private - cannot be seen by staff'),
    ('SH', 'Shared'),
  )
  privacy = models.CharField(max_length=2, choices=PRIVACY_CHOICES, default='SH')
  amount = models.PositiveIntegerField(verbose_name='*Amount to ask ($)')
  likelihood = models.PositiveIntegerField(verbose_name='*Estimated likelihood (%)', validators=[MaxValueValidator(100)])
  talked = models.BooleanField(default=False)
  asked = models.BooleanField(default=False)
  pledged = models.PositiveIntegerField(blank=True, null=True)
  gifted = models.PositiveIntegerField(default=0)
  gift_notified = models.BooleanField(default=False)
  phone = models.CharField(max_length=15, null=True, blank=True)
  email = models.EmailField(null=True, blank=True)
  notes = models.TextField(blank=True)
  
  next_step = models.ForeignKey('Step', related_name = '+', null=True) #don't need to go backwards
  
  def __unicode__(self):
    return self.firstname+' '+self.lastname
  
  def estimated(self):
    return int(self.amount*self.likelihood*.01)
  
  def get_next_step(self):
    step = Step.objects.filter(donor=self, completed__isnull=True)
    if step:
      return step[0]
    else:
      return None
    
  def get_steps(self): #used in expanded view
    return Step.objects.filter(donor=self).filter(completed__isnull=False).order_by('date')
  
  def has_overdue(self):
    steps = Step.objects.filter(donor=self, completed__isnull=True)
    for step in steps:
      if step.date < timezone.now().date():
        return timezone.now().date()-step.date
    return False
  
def make_custom_datefield(f):
  """date selector implementation from http://strattonbrazil.blogspot.com/2011/03/using-jquery-uis-date-picker-on-all.html """
  formfield = f.formfield()
  if isinstance(f, models.DateField):
      formfield.widget.format = '%m/%d/%Y'
      formfield.widget.attrs.update({'class':'datePicker', 'readonly':'true'})
  return formfield
    
class DonorForm(ModelForm): #used to edit, creation uses custom form
  class Meta:
    model = Donor
    fields = ('firstname', 'lastname', 'amount', 'likelihood', 'phone', 'email', 'asked', 'pledged', 'notes')

class Step(models.Model):  
  created = models.DateTimeField(auto_now=True)
  date = models.DateField(verbose_name='Date')
  description = models.CharField(max_length=255, verbose_name='Description')
  donor = models.ForeignKey(Donor)
  completed = models.DateTimeField(null=True)
  asked = models.BooleanField(default=False)
  pledged = models.PositiveIntegerField(blank=True, null=True)

  def __unicode__(self):
    return unicode(self.date.strftime('%m/%d/%y')) + u' -  ' + self.description
    
class StepForm(ModelForm):
  formfield_callback = make_custom_datefield #date input
  
  class Meta:
    model = Step
    exclude = ('donor', 'completed', 'asked', 'pledged')
    
class NewsItem(models.Model):
  date = models.DateTimeField(auto_now=True)
  updated = models.DateTimeField(auto_now_add=True)
  membership = models.ForeignKey(Membership)
  summary = models.TextField()
  
  def __unicode__(self):
    return unicode(self.summary)

class Event(models.Model):
  desc = models.CharField(max_length=255)
  date = models.DateTimeField()
  project = models.ForeignKey(GivingProject)
  location = models.CharField(max_length=255, null=True, blank=True)
  link = models.URLField(null=True, blank=True)
  def __unicode__(self):
    return self.desc

class Resource(models.Model):
  title = models.CharField(max_length=255)
  summary = models.TextField(blank=True)
  link = models.URLField()
  
  def __unicode__(self):
    return self.title

class ProjectResource(models.Model): #ties resource to project
  giving_project = models.ForeignKey(GivingProject)
  resource = models.ForeignKey(Resource)
  
  session = models.CharField(max_length=255)