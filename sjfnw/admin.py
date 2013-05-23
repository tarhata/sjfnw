﻿from django.conf import settings
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.mail import EmailMultiAlternatives
from django.forms.widgets import HiddenInput
from django.http import HttpResponse
from django.forms import ValidationError
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from fund.models import *
from grants.models import *
from forms import IntegerCommaField
import unicodecsv as csv
import fund.forms, fund.utils
import logging, re

## Fund

# display methods
def step_membership(obj): #Step list_display
  return obj.donor.membership

def gp_year(obj): #GP list_display
  return obj.fundraising_deadline.year
gp_year.short_description = 'Year'

# actions
def approve(modeladmin, request, queryset): #Membership action
  logging.info('Approval button pressed; looking through queryset')
  for memship in queryset:
    if memship.approved == False:
      fund.utils.NotifyApproval(memship)
  queryset.update(approved=True)
  logging.info('Approval queryset updated')

def export_donors(modeladmin, request, queryset):
  logging.info('Export donors called by ' + request.user.email)
  response = HttpResponse(mimetype='text/csv')
  response['Content-Disposition'] = 'attachment; filename=prospects.csv'
  writer = csv.writer(response)

  writer.writerow(['First name', 'Last name', 'Phone', 'Email', 'Member', 'Giving Project', 'Amount to ask', 'Asked', 'Pledged', 'Gifted', 'Notes'])
  count = 0
  for donor in queryset:
    fields = [donor.firstname, donor.lastname, donor.phone, donor.email, donor.membership.member, donor.membership.giving_project, donor.amount, donor.asked, donor.pledged, donor.gifted, donor.notes]
    writer.writerow(fields)
    count += 1
  logging.info(str(count) + ' donors exported')
  return response

# Filters
class PledgedBooleanFilter(SimpleListFilter): #donors & steps
  title = 'pledged'
  parameter_name = 'pledged_tf'

  def lookups(self, request, model_admin):
      return (('True', 'Pledged'), ('False', 'Declined'), ('None', 'None entered'))

  def queryset(self, request, queryset):
    if self.value() == 'True':
      return queryset.filter(pledged__gt=0)
    if self.value() == 'False':
      return queryset.filter(pledged=0)
    elif self.value() == 'None':
      return queryset.filter(pledged__isnull=True)

class GiftedBooleanFilter(SimpleListFilter): #donors & steps
  title = 'gifted'
  parameter_name = 'gifted_tf'

  def lookups(self, request, model_admin):
      return (('True', 'Gift received'), ('False', 'No gift received'))

  def queryset(self, request, queryset):
    if self.value() == 'True':
      return queryset.filter(gifted__gt=0)
    if self.value() == 'False':
      return queryset.filter(gifted=0)

# Inlines
class MembershipInline(admin.TabularInline): #GP
  model = Membership
  formset = fund.forms.MembershipInlineFormset
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
  readonly_fields = ('firstname', 'lastname', 'amount', 'talked', 'asked', 'pledged')
  fields = ('firstname', 'lastname', 'amount', 'talked', 'asked', 'pledged')

# Forms
class GivingProjectAdminForm(ModelForm):
  fund_goal = IntegerCommaField(label='Fundraising goal', initial=0, help_text='Fundraising goal agreed upon by the group. If 0, it will not be displayed to members and they won\'t see a group progress chart for money raised.')

  class Meta:
    model = GivingProject

# ModelAdmin
class GivingProjectA(admin.ModelAdmin):
  list_display = ('title', gp_year, 'estimated')
  readonly_fields = ('estimated',)
  fields = (
    ('title', 'public'),
    ('fundraising_training', 'fundraising_deadline'),
    'fund_goal',
    'calendar',
    'suggested_steps',
    'pre_approved',
   )
  inlines = [ProjectResourcesInline, MembershipInline]
  form = GivingProjectAdminForm

class MemberAdvanced(admin.ModelAdmin): #advanced only
  list_display = ('first_name', 'last_name', 'email')
  search_fields = ['first_name', 'last_name', 'email']
  inlines = [MembershipInline]

class MembershipA(admin.ModelAdmin):
  list_display = ('member', 'giving_project', 'estimated', 'pledged', 'has_overdue', 'last_activity', 'approved', 'leader')
  readonly_list = ('estimated', 'pledged', 'has_overdue',)
  actions = [approve]
  list_filter = ('approved', 'leader', 'giving_project') #add overdue steps
  search_fields = ['member__first_name', 'member__last_name']
  inlines = [DonorInline]

class DonorA(admin.ModelAdmin):
  list_display = ('firstname', 'lastname', 'membership', 'amount', 'talked', 'pledged', 'gifted')
  list_filter = ('membership__giving_project', 'asked', PledgedBooleanFilter, GiftedBooleanFilter)
  list_editable = ('gifted',)
  exclude = ('added',)
  search_fields = ['firstname', 'lastname', 'membership__member__first_name', 'membership__member__last_name']
  actions = [export_donors]

class NewsA(admin.ModelAdmin):
  list_display = ('summary', 'date', 'membership')
  list_filter = ('membership__giving_project',)

class StepAdv(admin.ModelAdmin): #adv only
  list_display = ('description', 'donor', step_membership, 'date', 'completed', 'pledged')
  list_filter = ('donor__membership', PledgedBooleanFilter, GiftedBooleanFilter)

## Grants

# methods
def revert_grant(obj): #GrantApplication fieldset
  return '<a href="revert">Revert to draft</a>'
revert_grant.allow_tags = True

def rollover(obj): #GrantApplication fieldset
  return '<a href="rollover">Copy to another grant cycle</a>'
rollover.allow_tags = True

def organization_link(obj):
  return u'<a href="/admin/grants/organization/' + str(obj.organization.pk) + '/" target="_blank">' + unicode(obj.organization) + '</a>'
organization_link.allow_tags = True
organization_link.short_description = 'Organization'

def edit_application(obj): #GrantApplication fieldset
  return '<a href="/admin/grants/grantapplication/' + str(obj.pk) + '/" target="_blank">Edit</a>'
edit_application.allow_tags = True

def adv_viewdraft(obj): #Link from Draft inline on Org to Draft page
  return '<a href="/admin-advanced/grants/draftgrantapplication/' + str(obj.pk) + '/" target="_blank">View</a>'
adv_viewdraft.allow_tags = True

# inlines
class GrantApplicationCycleInline(admin.TabularInline): #Cycle
  model = GrantApplication
  extra = 0
  max_num = 0
  can_delete = False
  readonly_fields = ('organization', 'submission_time', 'screening_status')
  fields = ('organization', 'submission_time', 'screening_status')

class GrantApplicationInline(admin.TabularInline): #Org
  model = GrantApplication
  extra = 0
  max_num = 0
  can_delete = False
  readonly_fields = ('submission_time', 'grant_cycle', 'screening_status', edit_application, 'view_link')
  fields = ('submission_time', 'grant_cycle', 'screening_status', edit_application, 'view_link')

class DraftInline(admin.TabularInline): #Adv only
  model = DraftGrantApplication
  extra = 0
  max_num = 0
  can_delete = False
  readonly_fields = ('grant_cycle', 'modified', 'overdue', 'extended_deadline', adv_viewdraft)
  fields = ('grant_cycle', 'modified', 'overdue', 'extended_deadline', adv_viewdraft)

class GrantLogInlineRead(admin.TabularInline): #Org, Application
  model = GrantApplicationLog
  extra = 0
  max_num = 0
  fields = ('date', 'application', 'staff', 'contacted', 'notes')
  readonly_fields = ('date', 'application', 'staff', 'contacted', 'notes')
  verbose_name = 'Log'
  verbose_name_plural = 'Logs'

class GrantLogInline(admin.TabularInline): #Org, Application
  model = GrantApplicationLog
  extra = 1
  max_num = 1
  exclude = ('date',)
  can_delete = False
  verbose_name_plural = 'Add a log entry'

  def queryset(self, request):
    return GrantApplicationLog.objects.none()

  def formfield_for_foreignkey(self, db_field, request, **kwargs):
    if db_field.name == 'staff':
      kwargs['initial'] = request.user.id
      return db_field.formfield(**kwargs)
    elif 'grantapplication' in request.path and db_field.name == 'organization':
      id = int(request.path.split('/')[-2])
      app = GrantApplication.objects.get(pk=id)
      kwargs['initial'] = app.organization.pk
      return db_field.formfield(**kwargs)
    return super(GrantLogInline, self).formfield_for_foreignkey(db_field, request, **kwargs)

# forms
class AppAdminForm(ModelForm):

  def clean(self):
    cleaned_data = super(AppAdminForm, self).clean()
    status = cleaned_data.get("screening_status")
    if status >=100:
      logging.info('Require check details')
    return cleaned_data

  class Meta:
    model = GrantApplication

class DraftForm(ModelForm):
  class Meta:
    model = DraftGrantApplication

  def clean(self):
    cleaned_data = super(DraftForm, self).clean()
    org = cleaned_data.get('organization')
    cycle = cleaned_data.get('grant_cycle')
    if org and cycle:
      if GrantApplication.objects.filter(organization=org, grant_cycle=cycle):
        raise ValidationError('This organization has already submitted an application to this grant cycle.')
    return cleaned_data

# modeladmin
class GrantCycleA(admin.ModelAdmin):
  list_display = ('title', 'open', 'close')
  fields = (
    ('title', 'open', 'close'),
    ('info_page', 'email_signature'),
    'extra_question',
    'conflicts',
  )
  inlines = (GrantApplicationCycleInline,)

class OrganizationA(admin.ModelAdmin):
  list_display = ('name', 'email',)
  fieldsets = (
    ('', {
      'fields':(('name', 'email'),)
    }),
    ('', {
      'fields':(('address', 'city', 'state', 'zip'), ('telephone_number', 'fax_number', 'email_address', 'website'))
    }),
    ('', {
      'fields':(('status', 'ein'), ('founded', 'mission'))
    }),
    ('Fiscal sponsor info', {
      'classes':('collapse',),
      'fields':(('fiscal_org', 'fiscal_person'), ('fiscal_telephone', 'fiscal_address', 'fiscal_email'),'fiscal_letter')
    })
  )
  readonly_fields = ('fiscal_org', 'fiscal_person', 'fiscal_telephone', 'fiscal_address', 'fiscal_email', 'fiscal_letter')
  search_fields = ('name', 'email')
  inlines = [GrantApplicationInline, GrantLogInlineRead, GrantLogInline]

class OrganizationAdvA(OrganizationA):
  inlines = [GrantApplicationInline, DraftInline, GrantLogInlineRead, GrantLogInline]

class GrantApplicationA(admin.ModelAdmin):
  form = AppAdminForm
  fieldsets = (
    'Application', {'fields': ((organization_link, 'grant_cycle', 'submission_time', 'view_link'),)}
    ),(
    'Administration', {'fields': (('screening_status', 'giving_project'),('scoring_bonus_poc', 'scoring_bonus_geo'), (revert_grant, rollover))}
    )
  readonly_fields = (organization_link, 'grant_cycle', 'submission_time', 'view_link', revert_grant, rollover)
  list_display = ('organization', 'grant_cycle', 'submission_time', 'screening_status', 'view_link')
  list_filter = ('grant_cycle', 'screening_status')
  inlines = [GrantLogInlineRead, GrantLogInline]

  def has_add_permission(self, request):
    return False

class DraftGrantApplicationA(admin.ModelAdmin):
  list_display = ('organization', 'grant_cycle', 'modified', 'overdue', 'extended_deadline')
  list_filter = ('grant_cycle',) #extended
  fields = (('organization', 'grant_cycle', 'modified'), ('extended_deadline'))
  readonly_fields = ('modified',)
  form = DraftForm

  def get_readonly_fields(self, request, obj=None):
    if obj is not None: #editing - lock org & cycle
      return self.readonly_fields + ('organization', 'grant_cycle')
    return self.readonly_fields

class DraftAdv(admin.ModelAdmin): #Advanced
  list_display = ('organization', 'grant_cycle', 'modified', 'overdue', 'extended_deadline')
  list_filter = ('grant_cycle',) #extended
  fields = (('organization', 'grant_cycle', 'created', 'modified', 'modified_by'), 'contents', 'budget', 'demographics', 'funding_sources', 'fiscal_letter', 'budget1', 'budget2', 'budget3', 'project_budget_file',)
  readonly_fields = ('organization', 'grant_cycle', 'modified', 'budget', 'demographics', 'funding_sources', 'fiscal_letter', 'budget1', 'budget2', 'budget3', 'project_budget_file',)

# Register - basic

#admin.site.unregister(User)
admin.site.unregister(Group)

admin.site.register(GivingProject, GivingProjectA)
admin.site.register(Membership, MembershipA)
admin.site.register(NewsItem, NewsA)
admin.site.register(Donor, DonorA)
admin.site.register(Resource)

admin.site.register(GrantCycle, GrantCycleA)
admin.site.register(Organization, OrganizationA)
admin.site.register(GrantApplication, GrantApplicationA)
admin.site.register(DraftGrantApplication, DraftGrantApplicationA)

# Register - Advanced

advanced_admin = AdminSite(name='advanced')

advanced_admin.register(User, UserAdmin)
advanced_admin.register(Group)
advanced_admin.register(Permission)
advanced_admin.register(ContentType)

advanced_admin.register(Member, MemberAdvanced)
advanced_admin.register(Donor, DonorA)
advanced_admin.register(Membership, MembershipA)
advanced_admin.register(GivingProject, GivingProjectA)
advanced_admin.register(NewsItem, NewsA)
advanced_admin.register(Step, StepAdv)
advanced_admin.register(ProjectResource)
advanced_admin.register(Resource)

advanced_admin.register(GrantCycle, GrantCycleA)
advanced_admin.register(Organization, OrganizationAdvA)
advanced_admin.register(GrantApplication, GrantApplicationA)
advanced_admin.register(DraftGrantApplication, DraftAdv)