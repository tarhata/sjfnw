from django.contrib import admin
from django.contrib.admin.helpers import InlineAdminFormSet
from django.core.urlresolvers import reverse
from django.db import connection
from django.http import HttpResponse
from django.forms import ValidationError, ModelForm
from django.forms.models import BaseInlineFormSet
from django.utils.safestring import mark_safe

from sjfnw.utils import log_queries
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
  intermediate = 'projectapp__application__grant_cycle'
  title = 'Grant cycle year'

class CycleTypeFilter(admin.SimpleListFilter):
  title = 'Grant cycle type'
  parameter_name = 'cycle_type'

  def lookups(self, request, model_admin):
    titles = GrantCycle.objects.order_by('title').values_list('title', flat=True).distinct()
    # group cycles into "types" - criminal justice, economic justice, etc.
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
      return queryset.filter(projectapp__application__grant_cycle__title__startswith=self.value())


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
  fields = ('date', 'grantcycle', 'staff', 'contacted', 'notes')
  readonly_fields = ('date', 'grantcycle', 'staff', 'contacted', 'notes')
  verbose_name = 'Log'
  verbose_name_plural = 'Logs'

  def queryset(self, request):
    return super(LogReadonlyI, self).queryset(request).select_related('staff', 'application', 'application__grant_cycle')

  def grantcycle(self, obj):
    if obj.application:
      return obj.application.grant_cycle
    else:
      return ''
  grantcycle.short_description = 'Application'


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
      # staff field
      if db_field.name == 'staff':  
        kwargs['initial'] = request.user.id
        kwargs['queryset'] = User.objects.filter(is_staff=True)
        return db_field.formfield(**kwargs)
      # organization field on app page
      elif 'grantapplication' in request.path and db_field.name == 'organization':
        id = int(request.path.split('/')[-2])
        app = GrantApplication.objects.get(pk=id)
        kwargs['initial'] = app.organization_id
        return db_field.formfield(**kwargs)
      # application field
      if db_field.name=='application':
        org_pk = int(request.path.split('/')[-2])
        kwargs['queryset'] = GrantApplication.objects.filter(organization_id=org_pk).select_related('organization', 'grant_cycle')

    return super(LogI, self).formfield_for_foreignkey(db_field, request, **kwargs)

class AwardI(BaseShowInline): # NOT IN USE CURRENTLY
  model = GivingProjectGrant
  fields = ('amount', 'check_mailed', 'agreement_mailed', 'edit_award')
  readonly_fields = fields
  template = 'admin/grants/givingprojectgrant/tabular_inline.html'

  def queryset(self, request):
    return super(AwardI, self).queryset(request).select_related()

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

  def queryset(self, request):
    return super(GrantApplicationI, self).queryset(request).select_related('grant_cycle')


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
  fields = ('giving_project', 'screening_status', 'granted', 'year_end_report')
  readonly_fields = ('granted', 'year_end_report')
  verbose_name = 'Giving project'
  verbose_name_plural = 'Giving projects'

  def granted(self, obj):
    """ For existing projectapps, shows grant amount or link to add a grant """
    if obj.pk:
      if hasattr(obj, 'givingprojectgrant'):
        award = obj.givingprojectgrant
        return mark_safe('<a target="_blank" href="/admin/grants/givingprojectgrant/' +
            str(award.pk) + '/">$' + str(award.amount) + '</a>')
      else:
        return mark_safe(
            '<a target="_blank" href="/admin/grants/givingprojectgrant/add/?projectapp=' +
            str(obj.pk) + '" target="_blank">Enter an award</a>')
    return ''

  def year_end_report(self, obj):
    if obj.pk:
      report = YearEndReport.objects.select_related('award').filter(
          award__projectapp_id = obj.pk)
      if report:
        return mark_safe('<a target="_blank" href="/admin/grants/yearendreport/' + 
            str(report[0].pk) + '/">View</a>')
    return ''


# MODELADMIN

class GrantCycleA(admin.ModelAdmin):
  list_display = ('title', 'open', 'close')
  fields = (
    ('title', 'open', 'close'),
    ('info_page', 'email_signature'),
    'private',
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
    ('Staff-entered contact info', {
       'fields': (('staff_contact_person', 'staff_contact_person_title',
                   'staff_contact_phone', 'staff_contact_email'),)
    }),
    ('Contact info from most recent application', {
      'fields':(('address', 'city', 'state', 'zip'),
                ('contact_person', 'contact_person_title', 'telephone_number',
                 'email_address'), 
                ('fax_number',  'website'))
    }),
    ('Organization info from most recent application', {
      'fields':(('founded', 'status', 'ein', 'mission'),)
    }),
    ('Fiscal sponsor info from most recent application', {
      'classes':('collapse',),
      'fields':(('fiscal_org', 'fiscal_person'),
                ('fiscal_telephone', 'fiscal_address', 'fiscal_email'))
    })
  )
  search_fields = ('name', 'email')
  inlines = ()

  def change_view(self, request, object_id, form_url='', extra_context=None):
    logger.info('OrganizationA.change_view()')
    self.inlines = (GrantApplicationI, SponsoredProgramI, LogReadonlyI, LogI)
    self.readonly_fields = ('address', 'city', 'state', 'zip', 'telephone_number',
        'fax_number', 'email_address', 'website', 'status', 'ein', 'founded',
        'mission', 'fiscal_org', 'fiscal_person', 'fiscal_telephone',
        'fiscal_address', 'fiscal_email', 'fiscal_letter', 'contact_person',
        'contact_person_title')
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
    ('Application contact info', {
        'classes': ('collapse',),
        'description':
            ('Contact information as entered in the grant application. '
              'You may edit this as needed.  Note that the contact information '
              'you see on the organization page is always from the most recent '
              'application, whether that is this or a different one.'),
          'fields': (('address', 'city', 'state', 'zip', 'telephone_number',
                     'fax_number', 'email_address', 'website'),
                   ('status', 'ein'))
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
  inlines = [ProjectAppI, LogReadonlyI, LogI]

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
  list_select_related = True
  list_display = ('organization_name', 'grant_cycle', 'giving_project',
      'amount', 'check_mailed', 'year_end_report_due')
  list_filter = ['agreement_mailed', CycleTypeFilter, GrantCycleYearFilter]
  exclude = ('created',)
  fields = (
      ('projectapp', 'amount'),
      ('check_number', 'check_mailed'),
      ('agreement_mailed', 'agreement_returned'),
      'approved',
      'year_end_report_due',
    )
  readonly_fields = ['year_end_report_due', 'grant_cycle',
                     'organization_name', 'giving_project']


  def formfield_for_foreignkey(self, db_field, request, **kwargs):
    if db_field.name == 'projectapp':
      pa = request.GET.get('projectapp')
      if pa:
        kwargs['queryset'] = ProjectApp.objects.filter(pk=pa).select_related('application', 'application__organization', 'giving_project')
    return super(GivingProjectGrantA, self).formfield_for_foreignkey(db_field, request, **kwargs)

  def year_end_report_due(self, obj):
    return obj.yearend_due()

  def organization_name(self, obj):
    return obj.projectapp.application.organization.name

  def grant_cycle(self, obj):
    return '%s %s' % (obj.projectapp.application.grant_cycle.title,
                      obj.projectapp.application.grant_cycle.close.year)

  def giving_project(self, obj):
    return unicode(obj.projectapp.giving_project)

  def get_readonly_fields(self, request, obj=None):
    logger.info(obj)
    if obj is not None: #editing - lock org & cycle
      self.readonly_fields.append('projectapp')
      return self.readonly_fields
    return self.readonly_fields

  def change_view(self, request, object_id, form_url='', extra_context=None):
    logger.info(connection.queries)
    prior = len(connection.queries)
    view = super(GivingProjectGrantA, self).change_view(request, object_id, form_url,
                                                 extra_context=extra_context)
    logger.info('Post view')
    log_queries(connection.queries)
    logger.info(str(len(connection.queries) - prior) + ' TOTAL QUERIES')
    return view


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

class YearEndReportA(admin.ModelAdmin):
  list_display = ('org', 'award', 'submitted', 'visible', 'view_link')
  list_select_related = True
  fieldsets = (
    ('', {
      'fields': ('award', 'submitted', 'view_link')
    }),
    ('', {
      'fields': ('visible',)
    }),
    ('Edit year end report', {
      'classes': ('collapse',),
      'fields': ('email', 'phone', 'website', 'summarize_last_year', 'goal_progress',
        'quantitative_measures', 'evaluation', 'achieved', 'collaboration', 'new_funding',
        'major_changes', 'total_size', 'donations_count', 'donations_count_prev')
    })
  )
      
  readonly_fields = ('award', 'submitted', 'view_link')

  def view_link(self, obj):
    if obj.pk:
      link =  '<a href="%s" target="_blank">View report</a>' % reverse('sjfnw.grants.views.view_yer', kwargs = {'report_id': obj.pk})
      return link
  view_link.allow_tags = True

  def org(self, obj):
    return obj.award.projectapp.application.organization.name


# REGISTER

admin.site.register(GrantCycle, GrantCycleA)
admin.site.register(Organization, OrganizationA)
admin.site.register(GrantApplication, GrantApplicationA)
admin.site.register(DraftGrantApplication, DraftGrantApplicationA)
admin.site.register(GivingProjectGrant, GivingProjectGrantA)
admin.site.register(SponsoredProgramGrant, SponsoredProgramGrantA)
admin.site.register(YearEndReport, YearEndReportA)

advanced_admin.register(GrantCycle, GrantCycleA)
advanced_admin.register(Organization, OrganizationAdvA)
advanced_admin.register(GrantApplication, GrantApplicationA)
advanced_admin.register(DraftGrantApplication, DraftAdv)
advanced_admin.register(GivingProjectGrant, GivingProjectGrantA)
advanced_admin.register(SponsoredProgramGrant, SponsoredProgramGrantA)

