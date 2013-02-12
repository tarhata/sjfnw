from django import forms
from django.core.validators import MaxValueValidator
from django.db import models
from django.forms import ModelForm
from django.utils import timezone
from utils import NotifyApproval
import datetime, logging
 
class GivingProject(models.Model):
  title = models.CharField(max_length=255)
  public = models.BooleanField(default=True, help_text='Whether this project should show in the dropdown menu for members registering or adding a project to their account.')
  
  #fundraising
  fundraising_training = models.DateTimeField(help_text='Date & time of fundraising training.  At this point the app will require members to enter an ask amount & estimated likelihood for each contact.')
  fundraising_deadline = models.DateField(help_text='Members will stop receiving reminder emails at this date.')
  fund_goal = models.PositiveIntegerField(verbose_name='Fundraising goal', default=0, help_text='Fundraising goal agreed upon by the group. If 0, it will not be displayed to members and they won\'t see a group progress chart for money raised.')
  pre_approved = models.TextField(null=True, blank=True, help_text='List of member emails, separated by commas.  Anyone who registers using an email on this list will have their account automatically approved.  IMPORTANT: Any syntax error can make this feature stop working; in that case memberships will default to requiring manual approval by an administrator.') #remove null from all char
  suggested_steps = models.TextField(default='Talk to about project\nInvite to SJF event\nSet up time to meet for the ask\nAsk\nFollow up\nThank', help_text='Displayed to users when they add a step.  Put each step on a new line')
  
  calendar = models.CharField(max_length=255, null=True, blank=True, help_text= 'Calendar ID of a google calendar - format: ____@group.calendar.google.com')
  resources = models.ManyToManyField('Resource', through = 'ProjectResource', null=True, blank=True)

  def __unicode__(self):
    return self.title+' '+unicode(self.fundraising_deadline.year)
  
  def require_estimates(self):
    return self.fundraising_training <= timezone.now()
  
  def save(self, *args, **kwargs):
    logging.info(self.suggested_steps.count('\r'))
    self.suggested_steps = self.suggested_steps.replace('\r', '')
    super(GivingProject, self).save(*args, **kwargs)
    
class Member(models.Model):
  email = models.EmailField()
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
  
  def save(self, *args, **kwargs):
    logging.debug('Custom membership save running')
    try:
      previous = Membership.objects.get(id=self.id)
      logging.debug('Previously: ' + str(previous.approved) + ', now: ' + str(self.approved))
      if self.approved and not previous.approved: #newly approved!
        logging.debug('Detected approval on save for ' + str(self))
        NotifyApproval(self)
    except Membership.DoesNotExist: pass
    super(Membership, self).save(*args, **kwargs)
    
  def has_overdue(self, next=False): # 1 db query
    cutoff = timezone.now().date() - datetime.timedelta(days=1)
    steps = Step.objects.filter(donor__membership = self, completed__isnull = True, date__lt = cutoff).order_by('-date')
    count = steps.count()
    if not next:
      return count
    elif count==0:
      return count, False
    else:
      return count, steps[0]

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
      if donor.amount and donor.likelihood:
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
  privacy = models.CharField(max_length=2, choices=PRIVACY_CHOICES, default='SH') #not in use
  
  amount = models.PositiveIntegerField(verbose_name='*Amount to ask ($)', null=True, blank=True)
  likelihood = models.PositiveIntegerField(verbose_name='*Estimated likelihood (%)', validators=[MaxValueValidator(100)], null=True, blank=True)
  
  talked = models.BooleanField(default=False)
  asked = models.BooleanField(default=False)
  pledged = models.PositiveIntegerField(blank=True, null=True)
  gifted = models.PositiveIntegerField(default=0)
  gift_notified = models.BooleanField(default=False)
  
  phone = models.CharField(max_length=15, null=True, blank=True)
  email = models.EmailField(null=True, blank=True)
  notes = models.TextField(blank=True)
  
  next_step = models.ForeignKey('Step', related_name = '+', null=True, blank=True) #don't need to go backwards
  
  def __unicode__(self):
    if self.lastname:
      return self.firstname+' '+self.lastname
    else:
      return self.firstname

  def estimated(self):
    if self.amount and self.likelihood:
      return int(self.amount*self.likelihood*.01)
    else:
      return 0
    
  def get_steps(self): #used in expanded view
    return Step.objects.filter(donor=self).filter(completed__isnull=False).order_by('date')
  
  def has_overdue(self): #needs update, if it's still used
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
    fields = ('firstname', 'lastname', 'amount', 'likelihood', 'phone', 'email', 'notes')
    widgets = {
      'notes': forms.Textarea(attrs={'cols': 25, 'rows': 4}),
    }

class DonorPreForm(ModelForm): #for editing prior to fund training
  class Meta:
    model = Donor
    fields = ('firstname', 'lastname', 'phone', 'email', 'notes')
    widgets = {
      'notes': forms.Textarea(attrs={'cols': 25, 'rows': 4}),
    }

class Step(models.Model):  
  created = models.DateTimeField(auto_now=True)
  date = models.DateField(verbose_name='Date')
  description = models.CharField(max_length=255, verbose_name='Description')
  donor = models.ForeignKey(Donor)
  completed = models.DateTimeField(null=True, blank=True)
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
  
  def __unicode__(self):
    return "%s - %s - %s" %(self.giving_project, self.session, self.resource) 