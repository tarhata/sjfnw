from fund.models import *
import fund.forms
from grants.models import *
from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

## FUND

""" signals needed:
  membership save - if approval added, send email
  user save - if is_staff, add to group?
  gp save - remove blank lines in s_steps
  """

class HiddenModelAdmin(admin.ModelAdmin):
  def get_model_perms(self, request):
    #Return empty perms dict thus hiding the model from admin index.
    return {} 

def approve(modeladmin, request, queryset):
  subject, from_email = 'Membership Approved', settings.APP_SEND_EMAIL
  logging.info('Approval button pressed; looking through queryset')
  for memship in queryset:
    logging.info('Looking at ' + memship.member.email)
    if memship.approved == False:
      to = memship.member.email
      logging.info('Approved was false, approval for ' + to + ' starting')
      html_content = render_to_string('fund/email_account_approved.html', {'login_url':settings.APP_BASE_URL + 'fund/login', 'project':memship.giving_project})
      text_content = strip_tags(html_content)
      msg = EmailMultiAlternatives(subject, text_content, from_email, [to], ['sjfnwads@gmail.com']) #bcc for testing
      msg.attach_alternative(html_content, "text/html")
      msg.send()    
      logging.info('Approval email sent to ' + to)      
  queryset.update(approved=True)
  logging.info('Approval queryset updated')    

def overdue_steps(obj):
  return obj.has_overdue()

def estimated(obj):
  return obj.estimated()
  
def pledged(obj):
  return obj.pledged()

class MembershipAdmin(admin.ModelAdmin): #todo add overdue steps filter
  list_display = ('member', 'giving_project', estimated, pledged, overdue_steps, 'last_activity', 'approved', 'leader')
  actions = [approve]
  list_filter = ('approved', 'leader', 'giving_project')
  #readonly_fields = ('last_activity', 'emailed', 'approved')
  
class MembershipInline(admin.TabularInline):
  model = Membership
  formset = fund.forms.MembershipInlineFormset
  extra = 0
  fieldsets = (None, {
    'classes': ('collapse',),
    'fields': ('member', 'approved', 'leader',)
  }),

class MemberInline(admin.TabularInline):
  model = Member
  extra = 1

class ProjectResourcesInline(admin.TabularInline):
  model = ProjectResource
  extra = 0
  fieldsets = (None, {
    'classes': ('collapse',),
    'fields': ('resource', 'session',)
  }),

def gp_year(obj):
  return obj.fundraising_deadline.year
gp_year.short_description = 'Year'

class GPAdmin(admin.ModelAdmin):
  list_display = ('title', gp_year)
  inlines = [
    ProjectResourcesInline,
    MembershipInline,
  ]
  
class DonorAdmin(admin.ModelAdmin):
  list_display = ('firstname', 'lastname', 'membership', 'amount', 'pledged', 'gifted')
  list_filter = ('membership__giving_project',)
  list_editable = ('gifted',)
  search_fields = ['firstname', 'lastname']

class NewsAdmin(admin.ModelAdmin):
  list_display = ('summary', 'date', 'membership')
  list_filter = ('membership__giving_project',)

  #advanced
class DonorAdvanced(admin.ModelAdmin):
  list_display = ('__unicode__', 'membership', 'asked', 'pledged', 'gifted')
  list_filter = ('asked', 'membership__giving_project')
  search_fields = ['firstname', 'lastname']
  
class MembershipAdvanced(admin.ModelAdmin):
  list_display = ('member', 'giving_project', estimated, pledged, overdue_steps, 'last_activity', 'approved', 'leader')
  actions = [approve]
  list_filter = ('approved', 'leader', 'giving_project')

class MemberAdvanced(admin.ModelAdmin):
  list_display = ('__unicode__', 'email')
  search_fields = ['first_name', 'last_name', 'email']
  def get_model_perms(self, request):
    #Return empty perms dict thus hiding the model from admin index.
    return {}
  

def step_membership(obj):
  return obj.donor.membership

class MembershipAdvanced(admin.ModelAdmin):
  list_display = ('member', 'giving_project', estimated, pledged, overdue_steps, 'last_activity', 'approved', 'leader')
  actions = [approve]
  list_filter = ('approved', 'leader', 'giving_project') 

class StepAdv(admin.ModelAdmin):
  list_display = ('description', 'donor', step_membership, 'date', 'completed')

## GRANTS

class GrantAppAdmin(admin.ModelAdmin):
  fields = ('screening_status', 'grant_cycle', 'scoring_bonus_poc', 'scoring_bonus_geo')
  list_display = ('organization', 'submission_time', 'screening_status')  

class DraftAdmin(admin.ModelAdmin):
  list_display = ('organization', 'grant_cycle', 'modified')

class OrganizationAdmin(admin.ModelAdmin):
  list_display = ('name', 'email',)
  list_editable = ('email',)

## ADMIN SITES

#default
#admin.site.unregister(User) # have to make contrib/auth/admin.py load first..
admin.site.register(Member, MemberAdvanced)
admin.site.register(GivingProject, GPAdmin)
admin.site.register(Membership, MembershipAdmin)
admin.site.register(NewsItem, NewsAdmin)
admin.site.register(Donor, DonorAdmin)
admin.site.register(ProjectResource)
admin.site.register(Resource)


#advanced
advanced_admin = AdminSite(name='advanced')

advanced_admin.register(User, UserAdmin)
advanced_admin.register(Group)

advanced_admin.register(Member, MemberAdvanced)
advanced_admin.register(Donor, DonorAdvanced)
advanced_admin.register(Membership, MembershipAdvanced)
advanced_admin.register(GivingProject, GPAdmin)
advanced_admin.register(NewsItem, NewsAdmin)
advanced_admin.register(Step, StepAdv)
advanced_admin.register(ProjectResource)
advanced_admin.register(Resource)

advanced_admin.register(GrantCycle)
advanced_admin.register(Organization, OrganizationAdmin)
advanced_admin.register(GrantApplication, GrantAppAdmin)
advanced_admin.register(DraftGrantApplication, DraftAdmin)