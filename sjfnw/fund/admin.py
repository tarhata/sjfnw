from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.http import HttpResponse
from django.forms import ValidationError

from sjfnw.admin import advanced_admin
from sjfnw.fund.models import *
from sjfnw.fund import forms, utils, modelforms
from sjfnw.grants.models import ProjectApp

import unicodecsv, logging

logger = logging.getLogger('sjfnw')

# display methods
def step_membership(obj): #Step list_display
  return obj.donor.membership

def gp_year(obj): #GP list_display
  return obj.fundraising_deadline.year
gp_year.short_description = 'Year'

def ship_progress(obj):
  return ('<table><tr><td style="width:33%;padding:1px;">$' +
          str(obj.estimated()) + '</td><td style="width:33%;padding:1px;">$' +
          str(obj.promised()) + '</td><td style="width:33%;padding:1px;">$' +
          str(obj.received()) + '</td></tr></table>')
ship_progress.short_description = 'Estimated, promised, received'
ship_progress.allow_tags = True

# actions
def approve(modeladmin, request, queryset): #Membership action
  logger.info('Approval button pressed; looking through queryset')
  for memship in queryset:
    if memship.approved == False:
      utils.NotifyApproval(memship)
  queryset.update(approved=True)
  logger.info('Approval queryset updated')

def export_donors(modeladmin, request, queryset):
  logger.info('Export donors called by ' + request.user.email)
  response = HttpResponse(mimetype='text/csv')
  response['Content-Disposition'] = 'attachment; filename=prospects.csv'
  writer = unicodecsv.writer(response)

  writer.writerow(['First name', 'Last name', 'Phone', 'Email', 'Member',
                   'Giving Project', 'Amount to ask', 'Asked', 'Promised',
                   'Received', 'Notes'])
  count = 0
  for donor in queryset:
    fields = [donor.firstname, donor.lastname, donor.phone, donor.email,
              donor.membership.member, donor.membership.giving_project,
              donor.amount, donor.asked, donor.promised, donor.received,
              donor.notes]
    writer.writerow(fields)
    count += 1
  logger.info(str(count) + ' donors exported')
  return response

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
      return queryset.filter(received__gt=0)
    if self.value() == 'False':
      return queryset.filter(received=0)

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


# ModelAdmin
class GivingProjectA(admin.ModelAdmin):
  list_display = ('title', gp_year, 'estimated')
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
  list_display = ('member', 'giving_project', ship_progress, 'overdue_steps',
                  'last_activity', 'approved', 'leader')
  readonly_list = (ship_progress, 'overdue_steps',)
  actions = [approve]
  list_filter = ('approved', 'leader', 'giving_project') #add overdue steps
  search_fields = ['member__first_name', 'member__last_name']
  inlines = [DonorInline]

class DonorA(admin.ModelAdmin):
  list_display = ('firstname', 'lastname', 'membership', 'amount', 'talked',
                  'promised', 'received')
  list_filter = ('membership__giving_project', 'asked', PromisedBooleanFilter,
                 ReceivedBooleanFilter)
  list_editable = ('received',)
  exclude = ('added',)
  search_fields = ['firstname', 'lastname', 'membership__member__first_name',
                   'membership__member__last_name']
  actions = [export_donors]

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
  
  def save_model(self, request, obj, form, change):
    obj.updated = timezone.now()
    obj.updated_by = request.user.username
    obj.save()

admin.site.register(GivingProject, GivingProjectA)
admin.site.register(Membership, MembershipA)
admin.site.register(NewsItem, NewsA)
admin.site.register(Donor, DonorA)
admin.site.register(Resource)
admin.site.register(Survey, SurveyA)

advanced_admin.register(Member, MemberAdvanced)
advanced_admin.register(Donor, DonorA)
advanced_admin.register(Membership, MembershipA)
advanced_admin.register(GivingProject, GivingProjectA)
advanced_admin.register(NewsItem, NewsA)
advanced_admin.register(Step, StepAdv)
advanced_admin.register(ProjectResource)
advanced_admin.register(Resource)

