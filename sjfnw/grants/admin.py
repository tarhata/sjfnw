from django.contrib import admin
from django.contrib.admin.helpers import InlineAdminFormSet
from django.http import HttpResponse
from django.forms import ValidationError, ModelForm
from django.forms.models import BaseInlineFormSet
from django.utils.safestring import mark_safe

from sjfnw.admin import advanced_admin, YearFilter
from sjfnw.grants.models import *
from sjfnw.grants.modelforms import DraftAdminForm

import unicodecsv as csv
import logging, re
logger = logging.getLogger('sjfnw')


# CUSTOM FILTERS

class GrantCycleYearFilter(YearFilter):
  filter_model = GrantCycle
  field = 'close'
  intermediate = 'project_app__application__grant_cycle'
  title = 'Grant cycle year'

class CycleTypeFilter(admin.SimpleListFilter):
  title = 'Grant cycle type'
  parameter_name = 'cycle_type'

  def lookups(self, request, model_admin):
    titles = GrantCycle.objects.order_by('title').values_list('title', flat=True).distinct()
    types = []
    for title in titles:
      pos = title.find(' Grant Cycle')
      if pos > 1:
        cycle_type = title[:pos]
        if not cycle_type in types:
          types.append(cycle_type)
      else: #Grant Cycle not found - just use whole
        if not title in types:
          types.append(title)
    return [(t, t) for t in types]

  def queryset(self, request, queryset):
    if not self.value():
      return queryset
    else:
      return queryset.filter(application__grant_cycle__title__startswith=self.value())


# INLINES

class BaseShowInline(admin.TabularInline):
  extra = 0
  max_num = 0
  can_delete = False

  class Meta:
    abstract = True

class LogReadonlyI(admin.TabularInline): #Org, Application
  model = GrantApplicationLog
  extra = 0
  max_num = 0
  fields = ('date', 'application', 'staff', 'contacted', 'notes')
  readonly_fields = ('date', 'application', 'staff', 'contacted', 'notes')
  verbose_name = 'Log'
  verbose_name_plural = 'Logs'

class LogI(admin.TabularInline): #Org, Application
  """ Inline for adding a log to an org or application
  Shows one blank row.  Autofills org or app depending on current page """
  model = GrantApplicationLog
  extra = 1
  max_num = 1
  exclude = ('date',)
  can_delete = False
  verbose_name_plural = 'Add a log entry'

  def queryset(self, request):
    return GrantApplicationLog.objects.none()

  def formfield_for_foreignkey(self, db_field, request, **kwargs):
    """ give initial values for staff and/or org """
    if '/add' in request.path:
      logger.info('LogI.formfield_for_foreignkey called on add view')
    else:
      if db_field.name == 'staff':
        kwargs['initial'] = request.user.id
        return db_field.formfield(**kwargs)
      elif 'grantapplication' in request.path and db_field.name == 'organization':
        id = int(request.path.split('/')[-2])
        app = GrantApplication.objects.get(pk=id)
        kwargs['initial'] = app.organization.pk
        return db_field.formfield(**kwargs)
      if db_field.name=='application':
        org_pk = int(request.path.split('/')[-2])
        kwargs['queryset'] = GrantApplication.objects.filter(organization_id=org_pk)
    return super(LogI, self).formfield_for_foreignkey(db_field, request, **kwargs)

class AwardI(BaseShowInline): #App, GP
  model = GivingProjectGrant
  fields = ('amount', 'check_mailed', 'agreement_mailed', 'edit_award')
  readonly_fields = fields
  template = 'admin/grants/givingprojectgrant/tabular_inline.html'

  def edit_award(self, obj):
    if obj.pk:
      return ('<a href="/admin/grants/givingprojectgrant/' + str(obj.pk) +
            '/" target="_blank">Edit</a>')
    else:
      return ''
  edit_award.allow_tags = True

class AppCycleI(BaseShowInline): #Cycle
  model = GrantApplication
  readonly_fields = ('organization', 'submission_time', 'pre_screening_status')
  fields = ('organization', 'submission_time', 'pre_screening_status')

class GrantApplicationI(BaseShowInline): #Org
  model = GrantApplication
  readonly_fields = ('submission_time', 'grant_cycle', 'pre_screening_status',
                     'edit_application', 'view_link')
  fields = ('submission_time', 'grant_cycle', 'pre_screening_status',
            'edit_application', 'view_link')

  def edit_application(self, obj): #GrantApplication fieldset
    return ('<a href="/admin/grants/grantapplication/' + str(obj.pk) +
            '/" target="_blank">Edit</a>')
  edit_application.allow_tags = True

class SponsoredProgramI(BaseShowInline): # Org
  model = SponsoredProgramGrant
  fields = ('amount', 'check_mailed', 'approved', 'edit')
  readonly_fields = fields
  template = 'admin/grants/sponsoredprogramgrant/tabular.html'

  def edit(self, obj):
    if obj.pk:
      return ('<a href="/admin/grants/sponsoredprogramgrant/' + str(obj.pk) +
            '/" target="_blank">View/edit</a>')
    else:
      return ''
  edit.allow_tags = True

class DraftI(BaseShowInline): #Adv only
  model = DraftGrantApplication
  fields = ('grant_cycle', 'modified', 'overdue', 'extended_deadline', 'adv_viewdraft')
  readonly_fields = ('grant_cycle', 'modified', 'overdue', 'extended_deadline', 'adv_viewdraft')

  def adv_viewdraft(obj): #Link from Draft inline on Org to Draft page
    return '<a href="/admin-advanced/grants/draftgrantapplication/' + str(obj.pk) + '/" target="_blank">View</a>'
  adv_viewdraft.allow_tags = True

class ProjectAppI(admin.TabularInline): # GrantApplication
  model = ProjectApp
  extra = 1
  fields = ('giving_project', 'screening_status', 'granted')
  readonly_fields = ('granted',)
  verbose_name = 'Giving project'
  verbose_name_plural = 'Giving projects'

  def granted(self, obj):
    """ For existing projectapps, shows grant amount or link to add a grant """
    output = ''
    if obj.pk:
      logger.info(obj.pk)
      try:
        award = obj.givingprojectgrant
        logger.info('grant does exist')
        output = award.amount
      except GivingProjectGrant.DoesNotExist:
        output = mark_safe(
            '<a href="/admin/grants/givingprojectgrant/add/?project_app=' +
            str(obj.pk) + '" target="_blank">Enter an award</a>')
    return output


# MODELADMIN

class GrantCycleA(admin.ModelAdmin):
  list_display = ('title', 'open', 'close')
  fields = (
    ('title', 'open', 'close'),
    ('info_page', 'email_signature'),
    'extra_question',
    'conflicts',
  )
  inlines = (AppCycleI,)

class OrganizationA(admin.ModelAdmin):
  list_display = ('name', 'email',)
  fieldsets = (
    ('', {
      'fields':(('name', 'email'),)
    }),
    ('Contact info from most recent application', {
      'fields':(('address', 'city', 'state', 'zip'),
                ('telephone_number', 'fax_number', 'email_address', 'website'))
    }),
    ('Organization info from most recent application', {
      'fields':(('founded', 'status', 'ein', 'mission'),)
    }),
    ('Fiscal sponsor info from most recent application', {
      'classes':('collapse',),
      'fields':(('fiscal_org', 'fiscal_person'),
                ('fiscal_telephone', 'fiscal_address', 'fiscal_email'),
                'fiscal_letter')
    })
  )
  search_fields = ('name', 'email')
  inlines = ()

  def change_view(self, request, object_id, form_url='', extra_context=None):
    logger.info('OrganizationA.change_view()')
    self.inlines = (GrantApplicationI, SponsoredProgramI,
                    LogReadonlyI, LogI)
    self.readonly_fields = ('address', 'city', 'state', 'zip', 'telephone_number',
        'fax_number', 'email_address', 'website', 'status', 'ein', 'founded',
        'mission', 'fiscal_org', 'fiscal_person', 'fiscal_telephone',
        'fiscal_address', 'fiscal_email', 'fiscal_letter')
    return super(OrganizationA, self).change_view(request, object_id)

class OrganizationAdvA(OrganizationA):
  inlines = [GrantApplicationI, DraftI, LogReadonlyI,
             LogI]

class GrantApplicationA(admin.ModelAdmin):
  fieldsets = (
    ('Application', {
        'fields': (('organization_link', 'grant_cycle', 'submission_time',
                   'view_link'),)
    }),
    ('Administration', {
        'fields': (('pre_screening_status', 'scoring_bonus_poc', 'scoring_bonus_geo', 'site_visit_report'),
                   ('revert_grant', 'rollover'))
    })
  )
  readonly_fields = ('organization_link', 'grant_cycle', 'submission_time',
                     'view_link', 'revert_grant', 'rollover')
  list_display = ('organization', 'grant_cycle', 'submission_time',
                  'view_link')
  list_filter = ('grant_cycle',)
  search_fields = ('organization__name',)
  inlines = [ProjectAppI, LogReadonlyI, LogI] # AwardI

  def has_add_permission(self, request):
    return False

  def revert_grant(self, obj):
    return '<a href="revert">Revert to draft</a>'
  revert_grant.allow_tags = True

  def rollover(self, obj):
    return '<a href="rollover">Copy to another grant cycle</a>'
  rollover.allow_tags = True

  def organization_link(self, obj):
    return (u'<a href="/admin/grants/organization/' + str(obj.organization.pk)
            + '/" target="_blank">' + unicode(obj.organization) + '</a>')
  organization_link.allow_tags = True
  organization_link.short_description = 'Organization'

class DraftGrantApplicationA(admin.ModelAdmin):
  list_display = ('organization', 'grant_cycle', 'modified', 'overdue',
                  'extended_deadline')
  list_filter = ('grant_cycle',) #extended
  fields = (('organization', 'grant_cycle', 'modified'), ('extended_deadline'))
  readonly_fields = ('modified',)
  form = DraftAdminForm
  search_fields = ('organization__name',)

  def get_readonly_fields(self, request, obj=None):
    if obj is not None: #editing - lock org & cycle
      return self.readonly_fields + ('organization', 'grant_cycle')
    return self.readonly_fields

class DraftAdv(admin.ModelAdmin): #Advanced
  list_display = ('organization', 'grant_cycle', 'modified', 'overdue',
                  'extended_deadline')
  list_filter = ('grant_cycle',) #extended

class GivingProjectGrantA(admin.ModelAdmin):
  list_display = ('organization_name', 'grant_cycle', 'giving_project',
      'amount', 'check_mailed', 'year_end_report_due')
  list_filter = ['agreement_mailed', CycleTypeFilter, GrantCycleYearFilter]
  exclude = ('created',)
  fields = (
      ('project_app', 'amount'),
      ('check_number', 'check_mailed'),
      ('agreement_mailed', 'agreement_returned'),
      'approved',
      'year_end_report_due',
    )
  readonly_fields = ('year_end_report_due', 'grant_cycle',
                     'organization_name', 'giving_project')

  def year_end_report_due(self, obj):
    return obj.yearend_due()

  def organization_name(self, obj):
    return obj.project_app.application.organization.name

  def grant_cycle(self, obj):
    return '%s %s' % (obj.project_app.application.grant_cycle.title,
                      obj.project_app.application.grant_cycle.close.year)

  def giving_project(self, obj):
    return unicode(obj.project_app.giving_project)

class SponsoredProgramGrantA(admin.ModelAdmin):
  list_display = ('organization', 'amount', 'check_mailed')
  list_filter = ('check_mailed',)
  exclude = ('entered',)
  fields = (
    ('organization', 'amount'),
    ('check_number', 'check_mailed', 'approved'),
    'description'
  )
  #readonly_fields = ()

# REGISTER

admin.site.register(GrantCycle, GrantCycleA)
admin.site.register(Organization, OrganizationA)
admin.site.register(GrantApplication, GrantApplicationA)
admin.site.register(DraftGrantApplication, DraftGrantApplicationA)
admin.site.register(GivingProjectGrant, GivingProjectGrantA)
admin.site.register(SponsoredProgramGrant, SponsoredProgramGrantA)

advanced_admin.register(GrantCycle, GrantCycleA)
advanced_admin.register(Organization, OrganizationAdvA)
advanced_admin.register(GrantApplication, GrantApplicationA)
advanced_admin.register(DraftGrantApplication, DraftAdv)
advanced_admin.register(GivingProjectGrant, GivingProjectGrantA)
advanced_admin.register(SponsoredProgramGrant, SponsoredProgramGrantA)

