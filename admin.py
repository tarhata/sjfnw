from django.conf import settings
from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from fund.models import *
from grants.models import *
import fund.forms, fund.utils
import logging

# Extra methods

def approve(modeladmin, request, queryset): #Membership action
  logging.info('Approval button pressed; looking through queryset')
  for memship in queryset:
    if memship.approved == False:
      fund.utils.NotifyApproval(memship)  
  queryset.update(approved=True)
  logging.info('Approval queryset updated')

def gp_year(obj): #GP list_display
  return obj.fundraising_deadline.year
gp_year.short_description = 'Year'

def revert_grant(obj): #GrantApplication fieldset
  return '<a href="revert">Revert to draft</a>'
revert_grant.allow_tags = True

def step_membership(obj): #Step list_display
  return obj.donor.membership

# Fund ModelAdmin

class MembershipInline(admin.TabularInline): #GP
  model = Membership
  formset = fund.forms.MembershipInlineFormset
  extra = 0
  can_delete = False
  fields = ('member', 'approved', 'leader',)

class ProjectResourcesInline(admin.TabularInline): #GP
  model = ProjectResource
  extra = 0
  template = 'admin/fund/tabular_projectresource.html'
  fields = ('resource', 'session',)

class GivingProjectA(admin.ModelAdmin):
  list_display = ('title', gp_year)
  fields = (
    ('title', 'public'),
    ('fundraising_training', 'fundraising_deadline'),
    'fund_goal',
    'calendar',
    'suggested_steps',
    'pre_approved',
   )
  inlines = [ProjectResourcesInline, MembershipInline]
  
class MemberAdvanced(admin.ModelAdmin): #advanced only
  list_display = ('__unicode__', 'email')
  search_fields = ['first_name', 'last_name', 'email']

class MembershipA(admin.ModelAdmin):
  list_display = ('member', 'giving_project', 'estimated', 'pledged', 'has_overdue', 'last_activity', 'approved', 'leader')
  readonly_list = ('estimated', 'pledged', 'has_overdue',)
  actions = [approve]
  list_filter = ('approved', 'leader', 'giving_project') #add overdue steps
 
class DonorA(admin.ModelAdmin):
  list_display = ('firstname', 'lastname', 'membership', 'amount', 'pledged', 'gifted')
  list_filter = ('membership__giving_project', 'asked')
  list_editable = ('gifted',)
  search_fields = ['firstname', 'lastname']

class NewsA(admin.ModelAdmin):
  list_display = ('summary', 'date', 'membership')
  list_filter = ('membership__giving_project',)

class StepAdv(admin.ModelAdmin): #adv only
  list_display = ('description', 'donor', step_membership, 'date', 'completed')

# Grant ModelAdmin

class GrantCycleA(admin.ModelAdmin):
  list_display = ('title', 'open', 'close')
  fields = (
    ('title', 'open', 'close'),
    ('addition', 'narrative')
  )

class GrantApplicationInline(admin.TabularInline): #Org
  model = GrantApplication
  extra = 0
  max_num = 0
  can_delete = False
  readonly_fields = ('submission_time', 'grant_cycle', 'screening_status')
  fields = ('submission_time', 'grant_cycle', 'screening_status')
  
class OrganizationA(admin.ModelAdmin):
  list_display = ('name', 'email',)
  fields = (
    ('name', 'email', 'telephone_number'),
    ('address', 'city', 'state', 'zip'),
    ('fiscal_letter'),
  )
  readonly_fields = ('address', 'city', 'state', 'zip', 'telephone_number', 'fax_number', 'email_address', 'website', 'status', 'ein', 'fiscal_letter')
  inlines = (GrantApplicationInline,)

class GrantApplicationA(admin.ModelAdmin):
  fieldsets = ('Summary', {'fields': (('organization', 'grant_cycle', 'submission_time'), 'view_link')}), ('Admin fields', {'fields': ('screening_status', ('scoring_bonus_poc', 'scoring_bonus_geo'), revert_grant)})
  readonly_fields = ('organization', 'grant_cycle', 'submission_time', 'view_link', revert_grant)
  list_display = ('organization', 'grant_cycle', 'submission_time', 'screening_status', 'view_link')  
  list_filter = ('grant_cycle', 'screening_status')

class DraftGrantApplicationA(admin.ModelAdmin):
  list_display = ('organization', 'grant_cycle', 'modified', 'overdue', 'extended_deadline')
  list_filter = ('grant_cycle',) #extended
  fields = (('organization', 'grant_cycle', 'modified'), ('extended_deadline'))
  readonly_fields = ('fiscal_letter', 'budget', 'demographics', 'funding_sources', 'modified',)
  
  def get_readonly_fields(self, request, obj=None):
    if obj is not None: #editing - lock org & cycle
      return self.readonly_fields + ('organization', 'grant_cycle')   
    return self.readonly_fields

class DraftAdv(admin.ModelAdmin):
  list_display = ('organization', 'grant_cycle', 'modified', 'overdue', 'extended_deadline')
  readonly_fields = ('organization', 'grant_cycle', 'modified', 'fiscal_letter', 'budget', 'demographics', 'funding_sources')

# Register - basic

admin.site.unregister(User)
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
advanced_admin.register(Organization, OrganizationA)
advanced_admin.register(GrantApplication, GrantApplicationA)
advanced_admin.register(DraftGrantApplication, DraftAdv)