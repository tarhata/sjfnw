from fund.models import *
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

    ## GENERAL ##

#admin.site.unregister(User) have to make contrib/auth/admin.py load first..

# advanced
logging.info('Creating adv_ad')
advanced_admin = AdminSite(name='advanced')

    ## FUND ##

""" signals needed:
membership save - if approval added, send email
user save - if is_staff, add to group?
"""

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
  readonly_fields = ('member', 'giving_project', 'last_activity', 'emailed', 'approved')

class MembershipInline(admin.TabularInline):
  model = Membership
  readonly_fields = ('member',)
  fieldsets = (None, {
                'classes': ('collapse',),
                'fields': ('member', 'approved', 'leader',)
              }),
  extra = 1

def gp_year(obj):
  return obj.fundraising_deadline.year
gp_year.short_description = 'Year'

class GPAdmin(admin.ModelAdmin):
  list_display = ('title', gp_year)
  fieldsets = (None, {'fields': ('title', 'fund_goal', 'fundraising_deadline', 'calendar', 'grant_cycle', 'pre_approved')}), ('Resources', {'classes': ('collapse',), 'fields': (('r1title', 'r1link'), ('r2title', 'r2link'), ('r3title', 'r3link'), ('r4title', 'r4link'), ('r5title', 'r5link'), ('r6title', 'r6link'), ('r7title', 'r7link'), ('r8title', 'r8link'), ('r9title', 'r9link'), ('r10title', 'r10link'))})
  inlines = [
        MembershipInline,
    ]

class DonorAdmin(admin.ModelAdmin):
  list_display = ('firstname', 'lastname', 'membership', 'amount', 'pledged', 'gifted')
  list_filter = ('membership__giving_project',)
  list_editable = ('gifted',)
  search_fields = ['firstname', 'lastname']

class EventAdmin(admin.ModelAdmin):
  list_display = ('desc', 'date', 'project')
  list_filter = ('project',)

class NewsAdmin(admin.ModelAdmin):
  list_display = ('short', 'date', 'project')
  list_filter = ('project',)

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

def step_membership(obj):
  return obj.donor.membership

class StepAdv(admin.ModelAdmin):
  list_display = ('description', 'donor', step_membership, 'date', 'complete')
  list_filter = ('complete',)

      ## GRANTS ##

class GrantAppAdmin(admin.ModelAdmin):
  fields = ('screening_status', 'grant_cycle', 'scoring_bonus_poc', 'scoring_bonus_geo')
  list_display = ('organization', 'submission_time', 'screening_status')  

class DraftAdmin(admin.ModelAdmin):
  list_display = ('organization', 'grant_cycle', 'modified')

class GranteeAdmin(admin.ModelAdmin):
  list_display = ('name', 'email',)
  list_editable = ('email',)

#default
admin.site.register(GivingProject, GPAdmin)
admin.site.register(Membership, MembershipAdmin)
admin.site.register(NewsItem, NewsAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Donor, DonorAdmin)

#advanced 
advanced_admin.register(User, UserAdmin)
advanced_admin.register(Group)

advanced_admin.register(Member, MemberAdvanced)
advanced_admin.register(Donor, DonorAdvanced)
advanced_admin.register(Membership, MembershipAdvanced)
advanced_admin.register(GivingProject, GPAdmin)
advanced_admin.register(NewsItem, NewsAdmin)
advanced_admin.register(Event, EventAdmin)
advanced_admin.register(Step, StepAdv)

advanced_admin.register(GrantCycle)
advanced_admin.register(NarrativeText)
advanced_admin.register(Grantee, GranteeAdmin)
advanced_admin.register(GrantApplication, GrantAppAdmin)
advanced_admin.register(SavedGrantApplication, DraftAdmin)