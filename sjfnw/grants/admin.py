from django.contrib import admin
from django.forms import ValidationError

from sjfnw.admin import advanced_admin

from .models import *
import unicodecsv as csv
import logging, re

# Forms
class AppAdminForm(ModelForm):
  def clean(self):
    cleaned_data = super(AppAdminForm, self).clean()
    status = cleaned_data.get("screening_status")
    if status >= 100:
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
        raise ValidationError('This organization has already submitted an '
                              'application to this grant cycle.')
    return cleaned_data

# Inlines
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
    """ give initial values for staff and/or org """
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
    return super(GrantLogInline, self).formfield_for_foreignkey(db_field, request, **kwargs)

class AwardInline(admin.TabularInline):
  model = GrantAward
  extra = 0
  max_num = 0
  fields = ('amount', 'check_mailed', 'agreement_mailed', 'edit_award')
  readonly_fields = ('amount', 'check_mailed', 'agreement_mailed', 'edit_award')
  can_delete = False
  template = 'admin/grants/grantaward/tabular_inline.html'

  def edit_award(self, obj):
    if obj.pk:
      return ('<a href="/admin/grants/grantaward/' + str(obj.pk) +
            '/" target="_blank">Edit</a>')
    else:
      return ''
  edit_award.allow_tags = True
  
class AppCycleInline(admin.TabularInline): #Cycle
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
  readonly_fields = ('submission_time', 'grant_cycle', 'screening_status',
                     'edit_application', 'view_link')
  fields = ('submission_time', 'grant_cycle', 'screening_status',
            'edit_application', 'view_link')

  def edit_application(self, obj): #GrantApplication fieldset
    return ('<a href="/admin/grants/grantapplication/' + str(obj.pk) +
            '/" target="_blank">Edit</a>')
  edit_application.allow_tags = True

# ModelAdmin
class GrantCycleA(admin.ModelAdmin):
  list_display = ('title', 'open', 'close')
  fields = (
    ('title', 'open', 'close'),
    ('info_page', 'email_signature'),
    'extra_question',
    'conflicts',
  )
  inlines = (AppCycleInline,)

class OrganizationA(admin.ModelAdmin):
  list_display = ('name', 'email',)
  fieldsets = (
    ('', {
      'fields':(('name', 'email'),)
    }),
    ('', {
      'fields':(('address', 'city', 'state', 'zip'),
                ('telephone_number', 'fax_number', 'email_address', 'website'))
    }),
    ('', {
      'fields':(('status', 'ein'), ('founded', 'mission'))
    }),
    ('Fiscal sponsor info', {
      'classes':('collapse',),
      'fields':(('fiscal_org', 'fiscal_person'),
                ('fiscal_telephone', 'fiscal_address', 'fiscal_email'),
                'fiscal_letter')
    })
  )
  readonly_fields = ('fiscal_org', 'fiscal_person', 'fiscal_telephone',
                     'fiscal_address', 'fiscal_email', 'fiscal_letter')
  search_fields = ('name', 'email')
  inlines = [GrantApplicationInline, GrantLogInlineRead, GrantLogInline]
  search_fields = ('name', 'email')

class DraftInline(admin.TabularInline): #Adv only
  model = DraftGrantApplication
  extra = 0
  max_num = 0
  can_delete = False
  readonly_fields = ('grant_cycle', 'modified', 'overdue', 'extended_deadline', 'adv_viewdraft')
  fields = ('grant_cycle', 'modified', 'overdue', 'extended_deadline', 'adv_viewdraft')

  def adv_viewdraft(obj): #Link from Draft inline on Org to Draft page
    return '<a href="/admin-advanced/grants/draftgrantapplication/' + str(obj.pk) + '/" target="_blank">View</a>'
  adv_viewdraft.allow_tags = True

class OrganizationAdvA(OrganizationA):
  inlines = [GrantApplicationInline, DraftInline, GrantLogInlineRead,
             GrantLogInline]

class GrantApplicationA(admin.ModelAdmin):
  form = AppAdminForm
  fieldsets = (
    ('Application', {
        'fields': (('organization_link', 'grant_cycle', 'submission_time',
                   'view_link'),)
    }),
    ('Administration', {
        'fields': (('screening_status', 'giving_project'),
                   ('scoring_bonus_poc', 'scoring_bonus_geo', 'site_visit_report'),
                   ('revert_grant', 'rollover'))
    })
  )
  readonly_fields = ('organization_link', 'grant_cycle', 'submission_time',
                     'view_link', 'revert_grant', 'rollover')
  list_display = ('organization', 'grant_cycle', 'submission_time',
                  'screening_status', 'view_link')
  list_filter = ('grant_cycle', 'screening_status')
  search_fields = ('organization__name',)
  inlines = [GrantLogInlineRead, GrantLogInline, AwardInline] # AwardInline

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
  form = DraftForm
  search_fields = ('organization__name',)

  def get_readonly_fields(self, request, obj=None):
    if obj is not None: #editing - lock org & cycle
      return self.readonly_fields + ('organization', 'grant_cycle')
    return self.readonly_fields

class DraftAdv(admin.ModelAdmin): #Advanced
  list_display = ('organization', 'grant_cycle', 'modified', 'overdue',
                  'extended_deadline')
  list_filter = ('grant_cycle',) #extended
  fields = (
    ('organization', 'grant_cycle', 'created', 'modified', 'modified_by'),
    'contents', 'budget', 'demographics', 'funding_sources', 'fiscal_letter',
    'budget1', 'budget2', 'budget3', 'project_budget_file',)
  readonly_fields = ('organization', 'grant_cycle', 'modified', 'budget',
                     'demographics', 'funding_sources', 'fiscal_letter',
                     'budget1', 'budget2', 'budget3', 'project_budget_file')

class GrantAwardA(admin.ModelAdmin):
  list_display = ('application', 'amount', 'check_mailed')
  list_filter = ('application__organization', 'application__giving_project')
  exclude = ('created',)
  fields = (
      ('application', 'amount'),
      ('check_number', 'check_mailed'),
      ('agreement_mailed', 'agreement_returned'),
      'approved',
    )

# Register

admin.site.register(GrantCycle, GrantCycleA)
admin.site.register(Organization, OrganizationA)
admin.site.register(GrantApplication, GrantApplicationA)
admin.site.register(DraftGrantApplication, DraftGrantApplicationA)
admin.site.register(GrantAward, GrantAwardA)

advanced_admin.register(GrantCycle, GrantCycleA)
advanced_admin.register(Organization, OrganizationAdvA)
advanced_admin.register(GrantApplication, GrantApplicationA)
advanced_admin.register(DraftGrantApplication, DraftAdv)
advanced_admin.register(GrantAward, GrantAwardA)

