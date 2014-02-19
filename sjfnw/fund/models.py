from django.contrib.humanize.templatetags.humanize import intcomma
from django.core.validators import MaxValueValidator
from django.db import models
from django.utils import timezone

from sjfnw.fund.utils import NotifyApproval

import datetime, logging

logger = logging.getLogger('sjfnw')

class GivingProject(models.Model):
  title = models.CharField(max_length=255)
  public = models.BooleanField(default=True,
                               help_text=('Whether this project should show in'
                               ' the dropdown menu for members registering or '
                               'adding a project to their account.'))

  pre_approved = models.TextField(blank=True,
      help_text=('List of member emails, separated by commas.  Anyone who '
      'registers using an email on this list will have their account '
      'automatically approved.  IMPORTANT: Any syntax error can make this '
      'feature stop working; in that case memberships will default to '
      'requiring manual approval by an administrator.'))

  #fundraising
  fundraising_training = models.DateTimeField(
      help_text=('Date & time of fundraising training.  At this point the app '
      'will require members to enter an ask amount & estimated likelihood for '
      'each contact.'))
  fundraising_deadline = models.DateField(
      help_text='Members will stop receiving reminder emails at this date.')
  fund_goal = models.PositiveIntegerField(
      verbose_name='Fundraising goal', default=0,
      help_text=('Fundraising goal agreed upon by the group. If 0, it will not '
        'be displayed to members and they won\'t see a group progress chart '
        'for money raised.'))
  suggested_steps = models.TextField(
      default=('Talk to about project\nInvite to SJF event\nSet up time to '
               'meet for the ask\nAsk\nFollow up\nThank'),
      help_text=('Displayed to users when they add a step.  Put each step on '
                 'a new line'))

  site_visits = models.BooleanField(default=False,
      help_text=('If checked, members will only see grants with a screening '
                'status of at least "site visit awarded"'))
  calendar = models.CharField(max_length=255, blank=True,
                              help_text= ('Calendar ID of a google calendar - '
                              'format: ____@group.calendar.google.com'))
  resources = models.ManyToManyField('Resource', through = 'ProjectResource',
                                     null=True, blank=True)
  surveys = models.ManyToManyField('Survey', through = 'GPSurvey',
                                   null=True, blank=True)

  class Meta:
    ordering = ['-fundraising_training']

  def __unicode__(self):
    return self.title+u' '+unicode(self.fundraising_deadline.year)

  def save(self, *args, **kwargs):
    self.suggested_steps = self.suggested_steps.replace('\r', '')
    super(GivingProject, self).save(*args, **kwargs)

  def require_estimates(self):
    return self.fundraising_training <= timezone.now()

  def estimated(self):
    donors = Donor.objects.filter(membership__giving_project=self)
    estimated = 0
    for donor in donors:
      estimated += donor.estimated()
    return estimated

class Member(models.Model):
  email = models.EmailField(max_length=100, unique=True)
  first_name = models.CharField(max_length=100)
  last_name = models.CharField(max_length=100)

  giving_project = models.ManyToManyField(GivingProject, through='Membership')
  current = models.IntegerField(default=0)

  def __unicode__(self):
    return unicode(self.first_name +u' '+self.last_name)

  class Meta:
    ordering = ['first_name', 'last_name']

class Membership(models.Model): #relationship b/n member and gp
  giving_project = models.ForeignKey(GivingProject)
  member = models.ForeignKey(Member)
  approved = models.BooleanField(default=False)
  leader = models.BooleanField(default=False)

  copied_contacts = models.BooleanField(default=False)
  #json encoded list of gp eval surveys completed
  completed_surveys = models.CharField(max_length=255, default='[]')

  emailed = models.DateField(
      blank=True, null=True,
      help_text=('Last time this member was sent an overdue steps reminder'))
  last_activity = models.DateField(
      blank=True, null=True,
      help_text=('Last activity by this user on this membership.'))

  notifications = models.TextField(default='', blank=True)

  class Meta:
    ordering = ['member']

  def __unicode__(self):
    return unicode(self.member)+u', '+unicode(self.giving_project)

  def save(self, skip=False, *args, **kwargs):
    if not skip:
      try:
        previous = Membership.objects.get(id=self.id)
        logger.debug('Previously: ' + str(previous.approved) + ', now: ' +
                      str(self.approved))
        if self.approved and not previous.approved: #newly approved!
          logger.debug('Detected approval on save for ' + unicode(self))
          NotifyApproval(self)
      except Membership.DoesNotExist:
        pass
    super(Membership, self).save(*args, **kwargs)

  def overdue_steps(self, get_next=False): # 1 db query
    cutoff = timezone.now().date() - datetime.timedelta(days=1)
    steps = Step.objects.filter(donor__membership = self, completed__isnull = True, date__lt = cutoff).order_by('-date')
    count = steps.count()
    if not get_next:
      return count
    elif count == 0:
      return count, False
    else:
      return count, steps[0]

  def asked(self): #remove
    return self.donor_set.filter(asked=True).count()

  def promised(self): #remove
    donors = self.donor_set.all()
    amt = 0
    for donor in donors:
      if donor.promised:
        amt = amt + donor.promised
    return amt

  def received(self): #remove
    donors = self.donor_set.all()
    amt = 0
    for donor in donors:
      amt = amt + donor.received()
    return amt

  def estimated(self): #remove
    estimated = 0
    donors = self.donor_set.all()
    for donor in donors:
      if donor.amount and donor.likelihood:
        estimated = estimated + donor.amount*donor.likelihood/100
    return estimated

  def update_story(self, timestamp):

    logger.info('update_story running for membership ' + str(self.pk) +
                 ' from ' + str(timestamp))

    #today's range
    today_min = timestamp.replace(hour=0, minute=0, second=0)
    today_max = timestamp.replace(hour=23, minute=59, second=59)

    #check for steps
    logger.debug("Getting steps")
    steps = Step.objects.filter(
        completed__range=(today_min, today_max),
        donor__membership = self).select_related('donor')
    if not steps:
      logger.warning('update story called on ' + str(self.pk) + 'but there are no steps')
      return

    #get or create newsitem object
    logger.debug('Checking for story with date between ' + str(today_min) +
                  ' and ' + str(today_max))
    search = self.newsitem_set.filter(date__range=(today_min, today_max))
    if search:
      story = search[0]
    else:
      story = NewsItem(date = timestamp, membership=self, summary = '')

    #tally today's steps
    talked, asked, promised = 0, 0, 0
    talkedlist = [] #for talk counts, don't want to double up
    askedlist = []
    for step in steps:
      logger.debug(unicode(step))
      if step.asked:
        asked += 1
        askedlist.append(step.donor)
        if step.donor in talkedlist: #if donor counted already, remove
          talked -= 1
          talkedlist.remove(step.donor)
      elif not step.donor in talkedlist and not step.donor in askedlist:
        talked += 1
        talkedlist.append(step.donor)
      if step.promised and step.promised > 0:
        promised += step.promised
    summary = self.member.first_name
    if talked > 0:
      summary += u' talked to ' + unicode(talked) + (u' people' if talked>1 else u' person')
      if asked > 0:
        if promised > 0:
          summary += u', asked ' + unicode(asked)
        else:
          summary += u' and asked ' + unicode(asked)
    elif asked > 0:
      summary += u' asked ' + unicode(asked) + (u' people' if asked>1 else u' person')
    else:
      logger.error('News update with 0 talked, 0 asked. Story pk: ' + str(story.pk))
    if promised > 0:
      summary += u' and got $' + unicode(intcomma(promised)) + u' in promises'
    summary += u'.'
    logger.info(summary)
    story.summary = summary
    story.updated = timezone.now()
    story.save()
    logger.info('Story saved')


class Donor(models.Model):
  added = models.DateTimeField(default=timezone.now())
  membership = models.ForeignKey(Membership)

  firstname = models.CharField(max_length=100, verbose_name='*First name')
  lastname = models.CharField(max_length=100, blank=True, verbose_name='Last name')

  amount = models.PositiveIntegerField(verbose_name='*Amount to ask ($)',
                                       null=True, blank=True)
  likelihood = models.PositiveIntegerField(verbose_name='*Estimated likelihood (%)',
                                           validators=[MaxValueValidator(100)],
                                           null=True, blank=True)

  talked = models.BooleanField(default=False)
  asked = models.BooleanField(default=False)
  promised = models.PositiveIntegerField(blank=True, null=True)
  received_this = models.PositiveIntegerField(default=0, verbose_name='Received - current year')
  received_next = models.PositiveIntegerField(default=0, verbose_name='Received - next year')
  received_afternext = models.PositiveIntegerField(default=0, verbose_name='Received - year after next')
  gift_notified = models.BooleanField(default=False)

  phone = models.CharField(max_length=15, blank=True)
  email = models.EmailField(max_length=100, blank=True)
  notes = models.TextField(blank=True)

  class Meta:
    ordering = ['firstname', 'lastname']

  def __unicode__(self):
    if self.lastname:
      return self.firstname + u' ' + self.lastname
    else:
      return self.firstname

  def estimated(self):
    if self.amount and self.likelihood:
      return int(self.amount*self.likelihood*.01)
    else:
      return 0

  def received(self):
    return self.received_this + self.received_next + self.received_afternext

  def get_steps(self): #used in expanded view
    return Step.objects.filter(donor=self).filter(completed__isnull=False).order_by('date')

  def has_overdue(self): #needs update, if it's still used
    steps = Step.objects.filter(donor=self, completed__isnull=True)
    for step in steps:
      if step.date < timezone.now().date():
        return timezone.now().date()-step.date
    return False

  def get_next_step(self):
    steps = self.step_set.filter(completed__isnull=True)
    if steps:
      return steps[0]
    else:
      return None

class Step(models.Model):
  created = models.DateTimeField(default=timezone.now())
  date = models.DateField(verbose_name='Date')
  description = models.CharField(max_length=255, verbose_name='Description')
  donor = models.ForeignKey(Donor)
  completed = models.DateTimeField(null=True, blank=True)
  asked = models.BooleanField(default=False)
  promised = models.PositiveIntegerField(blank=True, null=True)

  def __unicode__(self):
    return unicode(self.date.strftime('%m/%d/%y')) + u' -  ' + self.description


class NewsItem(models.Model):
  date = models.DateTimeField(default=timezone.now())
  updated = models.DateTimeField(default=timezone.now())
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
    return "%s - %s - %s" % (self.giving_project, self.session, self.resource)

class Survey(models.Model):

  created = models.DateTimeField(default=timezone.now())
  updated = models.DateTimeField(default=timezone.now())
  updated_by = models.CharField(max_length=100, blank=True)

  title = models.CharField(max_length=255, help_text=
      ('Descriptive summary to aid in sharing survey templates between '
       'projects. For admin site only. E.g. \'GP session evaluation\', '
       '\'Race workshop evaluation\', etc.'))
  intro = models.TextField(
      help_text=('Introductory text to display before the questions when form '
                 'is shown to GP members.'),
      default=('Please fill out this quick survey to let us know how the last '
               'meeting went.  Responses are anonymous, and once you fill out '
               'the survey you\'ll be taken to your regular home page.'))
  questions = models.TextField( #json encoded list of questions
      help_text=('Leave all of a question\' choices blank if you want a '
                 'write-in response instead of multiple choice'),
      default=('[{"question": "Did we meet our goals? (1=not at all, '
               '5=completely)", "choices": ["1", "2", "3", "4", "5"]}]'))

  def __unicode__(self):
    return self.title

  def save(self, *args, **kwargs):
    super(Survey, self).save(*args, **kwargs)
    logger.info('Survey saved. Questions are: ' + self.questions)


class GPSurvey(models.Model):
  survey = models.ForeignKey(Survey)
  giving_project = models.ForeignKey(GivingProject)
  date = models.DateTimeField()

  def __unicode__(self):
    return '%s - %s' % (self.giving_project.title, self.survey.title)

class SurveyResponse(models.Model):

  date = models.DateTimeField(default=timezone.now())
  gp_survey = models.ForeignKey(GPSurvey)
  responses = models.TextField() #json encoded question-answer pairs

  def __unicode__(self):
    return 'Response to %s %s survey' % (self.gp_survey.giving_project.title,
        self.date.strftime('%m/%d/%y'))

