from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.http import HttpResponse
from django.forms import ValidationError
from django.utils import timezone
from django.utils.safestring import mark_safe

from sjfnw.admin import advanced_admin
from sjfnw.fund.models import *
from sjfnw.fund import forms, utils, modelforms
from sjfnw.grants.models import ProjectApp

import unicodecsv, logging, json

logger = logging.getLogger('sjfnw')

# display methods
def step_membership(obj): #Step list_display
  return obj.donor.membership

def gp_year(obj): #GP list_display
  year = obj.fundraising_deadline.year
  if year == timezone.now().year:
    return '<b>%d</b>' % year
  else:
    return year
gp_year.short_description = 'Year'
gp_year.allow_tags = True


def ship_progress(obj):
  return ('<table><tr><td style="width:33%;padding:1px;">$' +
          str(obj.estimated()) + '</td><td style="width:33%;padding:1px;">$' +
          str(obj.promised()) + '</td><td style="width:33%;padding:1px;">$' +
          str(obj.received()) + '</td></tr></table>')
ship_progress.short_description = 'Estimated, promised, received'
ship_progress.allow_tags = True


# Filters
class PromisedBooleanFilter(SimpleListFilter): #donors & steps
  title = 'promised'
  parameter_name = 'promised_tf'

  def lookups(self, request, model_admin):
    return (('True', 'Promised'), ('False', 'Declined'),
              ('None', 'None entered'))

  def queryset(self, request, queryset):
    if self.value() == 'True':
      return queryset.filter(promised__gt=0)
    if self.value() == 'False':
      return queryset.filter(promised=0)
    elif self.value() == 'None':
      return queryset.filter(promised__isnull=True)

class ReceivedBooleanFilter(SimpleListFilter): #donors & steps
  title = 'received'
  parameter_name = 'received_tf'

  def lookups(self, request, model_admin):
    return (('True', 'Gift received'), ('False', 'No gift received'))

  def queryset(self, request, queryset):
    if self.value() == 'True':
      return queryset.exclude(
          received_this=0, received_next=0, received_afternext=0)
    if self.value() == 'False':
      return queryset.filter(
          received_this=0, received_next=0, received_afternext=0)


class GPYearFilter(SimpleListFilter):
  """ works for any object with a year attribute """
  title = 'year'
  parameter_name = 'year'
  
  def lookups(self, request, model_admin):
    deadlines = GivingProject.objects.values_list(
        'fundraising_deadline', flat=True
        ).order_by('-fundraising_deadline')
    prev = None
    years = []
    for deadline in deadlines:
      if deadline.year != prev:
        years.append((deadline.year, deadline.year))
        prev = deadline.year
    logger.info(years)
    return years

  def queryset(self, request, queryset):
    val = self.value()
    if not val:
      return queryset
    try:
      year = int(val)
    except:
      logger.error('GPYearFilter received invalid value %s' % val)
      messages.error(request,
          'Error loading filter. Contact techsupport@socialjusticefund.org')
      return queryset
    return queryset.filter(fundraising_deadline__year=year)
  

# Inlines
class MembershipInline(admin.TabularInline): #GP
  model = Membership
  formset = forms.MembershipInlineFormset
  extra = 0
  can_delete = False
  fields = ('member', 'giving_project', 'approved', 'leader',)

class ProjectResourcesInline(admin.TabularInline): #GP
  model = ProjectResource
  extra = 0
  template = 'admin/fund/tabular_projectresource.html'
  fields = ('resource', 'session',)

class DonorInline(admin.TabularInline): #membership
  model = Donor
  extra = 0
  max_num = 0
  can_delete = False
  readonly_fields = ('firstname', 'lastname', 'amount', 'talked', 'asked',
                     'promised')
  fields = ('firstname', 'lastname', 'amount', 'talked', 'asked', 'promised')

class ProjectAppInline(admin.TabularInline): # GivingProject
  model = ProjectApp
  extra = 1
  verbose_name = 'Grant application'
  verbose_name_plural = 'Grant applications'
  #readonly_fields = ('granted',)

  def granted(self, obj):
    """ For existing projectapps, shows grant amount or link to add a grant """
    output = ''
    if obj.pk:
      logger.info(obj.pk)
      try:
        award = obj.givingprojectgrant
      except GivingProjectGrant.DoesNotExist:
        output = mark_safe(
            '<a href="/admin/grants/givingprojectgrant/add/?project_app=' +
            str(obj.pk) + '" target="_blank">Enter an award</a>')
      else:
        logger.info('grant does exist')
        output = str(award.amount)
        logger.info(output)
    return output


class SurveyI(admin.TabularInline):

  model = GPSurvey
  extra = 1
  verbose_name = 'Survey'
  verbose_name_plural = 'Surveys'

# ModelAdmin
class GivingProjectA(admin.ModelAdmin):
  list_display = ('title', gp_year, 'estimated')
  list_filter = (GPYearFilter,)
  readonly_fields = ('estimated',)
  fields = (
    ('title', 'public'),
    ('fundraising_training', 'fundraising_deadline'),
    'fund_goal',
    'site_visits',
    'calendar',
    'suggested_steps',
    'pre_approved',
   )
  inlines = [SurveyI, ProjectResourcesInline, MembershipInline, ProjectAppInline]
  form = modelforms.GivingProjectAdminForm

class MemberAdvanced(admin.ModelAdmin): #advanced only
  list_display = ('first_name', 'last_name', 'email')
  search_fields = ['first_name', 'last_name', 'email']

class MembershipA(admin.ModelAdmin):

  actions = ['approve']
  list_display = ('member', 'giving_project', ship_progress, 'overdue_steps',
                  'last_activity', 'approved', 'leader')
  list_filter = ('approved', 'leader', 'giving_project') #add overdue steps
  search_fields = ['member__first_name', 'member__last_name']
  readonly_list = (ship_progress, 'overdue_steps',)

  fields = (('member', 'giving_project', 'approved'),
      ('leader', 'last_activity', 'emailed'),
      ('estimated', 'asked', 'promised', 'received'),
      'notifications'
  )
  readonly_fields = ('last_activity', 'emailed', 'estimated', 'asked', 'promised', 'received')
  inlines = [DonorInline]

  def approve(self, request, queryset): #Membership action
    logger.info('Approval button pressed; looking through queryset')
    for memship in queryset:
      if memship.approved == False:
        utils.NotifyApproval(memship)
    queryset.update(approved=True)
    logger.info('Approval queryset updated')


class DonorA(admin.ModelAdmin):
  list_display = ('firstname', 'lastname', 'membership', 'amount', 'talked',
                  'promised', 'received_this', 'received_next', 'received_afternext')
  list_filter = ('membership__giving_project', 'asked', PromisedBooleanFilter,
                 ReceivedBooleanFilter)
  list_editable = ('received_this', 'received_next', 'received_afternext')
  search_fields = ['firstname', 'lastname', 'membership__member__first_name',
                   'membership__member__last_name']
  actions = ['export_donors']

  fields = (('firstname', 'lastname'),
            ('phone', 'email'),
            ('amount', 'likelihood'),
            ('talked', 'asked', 'promised', 'promise_reason_display', 'likely_to_join'),
            ('received_this', 'received_next', 'received_afternext'),
            'notes')

  readonly_fields = ('membership', 'promise_reason_display', 'likely_to_join')

  def export_donors(self, request, queryset):
    logger.info('Export donors called by ' + request.user.email)

    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=prospects.csv'
    writer = unicodecsv.writer(response)

    writer.writerow(['First name', 'Last name', 'Phone', 'Email', 'Member',
                     'Giving Project', 'Amount to ask', 'Asked', 'Promised',
                     'Received - TOTAL', 'Received - Year', 'Received - Amount',
                     'Received - Year', 'Received - Amount',
                     'Received - Year', 'Received - Amount', 'Notes',
                     'Likelihood of joining a GP', 'Reasons for donating'])
    count = 0
    for donor in queryset:
      year = donor.membership.giving_project.fundraising_deadline.year
      fields = [donor.firstname, donor.lastname, donor.phone, donor.email,
                donor.membership.member, donor.membership.giving_project,
                donor.amount, donor.asked, donor.promised, donor.received(),
                year, donor.received_this, year+1, donor.received_next, year+2,
                donor.received_afternext, donor.notes,
                donor.get_likely_to_join_display(),
                donor.promise_reason_display()]
      writer.writerow(fields)
      count += 1
    logger.info(str(count) + ' donors exported')
    return response


class NewsA(admin.ModelAdmin):
  list_display = ('summary', 'date', 'membership')
  list_filter = ('membership__giving_project',)

class StepAdv(admin.ModelAdmin): #adv only
  list_display = ('description', 'donor', step_membership, 'date', 'completed',
                  'promised')
  list_filter = ('donor__membership', PromisedBooleanFilter,
                 ReceivedBooleanFilter)

class SurveyA(admin.ModelAdmin):
  list_display = ('title', 'updated')
  readonly_fields = ('updated',)
  form = modelforms.CreateSurvey
  fields = ('title', 'intro', 'questions')

  def save_model(self, request, obj, form, change):
    obj.updated = timezone.now()
    obj.updated_by = request.user.username
    obj.save()

class SurveyResponseA(admin.ModelAdmin):
  list_display = ('gp_survey', 'date')
  list_filter = ('gp_survey__giving_project',)
  fields = ('gp_survey', 'date', 'display_responses')
  readonly_fields = ('gp_survey', 'date', 'display_responses')
  actions = ['export_responses']

  def display_responses(self, obj):
    if obj and obj.responses:
      resp_list = json.loads(obj.responses)
      disp = '<table><tr><th>Question</th><th>Answer</th></tr>'
      for i in range(0, len(resp_list), 2):
        disp += ('<tr><td>' + str(resp_list[i]) + '</td><td>' +
                 str(resp_list[i+1]) + '</td></tr>')
      disp += '</table>'
      return mark_safe(disp)
  display_responses.short_description = 'Responses'

  def export_responses(self, request, queryset):

    logger.info('Export survey responses called by ' + request.user.email)
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=survey_responses %s.csv' % (timezone.now().strftime('%Y-%m-%d'),)
    writer = unicodecsv.writer(response)

    header = ['Date', 'Survey ID', 'Giving Project', 'Survey'] #base
    questions = 0
    response_rows = []
    for sr in queryset:
      fields = [sr.date, sr.gp_survey_id,
                sr.gp_survey.giving_project.title,
                sr.gp_survey.survey.title]
      logger.info(isinstance(sr.responses, str))
      qa = json.loads(sr.responses)
      for i in range(0, len(qa), 2):
        fields.append(qa[i])
        fields.append(qa[i+1])
        questions = max(questions, (i+2)/2)
      response_rows.append(fields)

    logger.info('Max %d questions' % questions)
    for i in range(0, questions):
      header.append('Question')
      header.append('Answer')
    writer.writerow(header)
    for row in response_rows:
      writer.writerow(row)

    return response

admin.site.register(GivingProject, GivingProjectA)
admin.site.register(Membership, MembershipA)
admin.site.register(NewsItem, NewsA)
admin.site.register(Donor, DonorA)
admin.site.register(Resource)
admin.site.register(Survey, SurveyA)
admin.site.register(SurveyResponse, SurveyResponseA)

advanced_admin.register(Member, MemberAdvanced)
advanced_admin.register(Donor, DonorA)
advanced_admin.register(Membership, MembershipA)
advanced_admin.register(GivingProject, GivingProjectA)
advanced_admin.register(NewsItem, NewsA)
advanced_admin.register(Step, StepAdv)
advanced_admin.register(ProjectResource)
advanced_admin.register(Resource)

