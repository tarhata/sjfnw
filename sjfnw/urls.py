from django.conf import settings
from django.conf.urls import patterns, include
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic.simple import direct_to_template
from admin import advanced_admin
from sjfnw import constants
import grants, fund, views

handler404 = 'views.page_not_found'
handler500 = 'views.server_error'

urlpatterns = patterns('',
  (r'^/?$', 'django.views.generic.simple.direct_to_template', {'template': 'home.html'}),

  # admin
  (r'^admin/', include(admin.site.urls)),
  (r'^admin$', views.admin_redirect),
  (r'^admin-advanced/', include(advanced_admin.urls)),
  (r'^admin-advanced$', views.admin_adv_redirect),

  # logout
  (r'^logout/?$', 'django.contrib.auth.views.logout', {'next_page': '/apply'}),
  (r'^fund/logout/?$', 'django.contrib.auth.views.logout', {'next_page': '/fund'}),

  # dev
  (r'^dev/jslog/?', 'views.log_javascript'),
  )

# password resets
urlpatterns += patterns('',
  # grants
  (r'^apply/reset/?$', 'django.contrib.auth.views.password_reset', {'template_name':'grants/reset.html', 'from_email':constants.GRANT_EMAIL, 'email_template_name':'grants/password_reset_email.html', 'post_reset_redirect':'/apply/reset-sent'}),
  (r'^apply/reset-sent/?', 'django.contrib.auth.views.password_reset_done', {'template_name':'grants/password_reset_done.html'}),
  (r'^apply/reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/?$', 'django.contrib.auth.views.password_reset_confirm', {'template_name':'grants/password_reset_confirm.html', 'post_reset_redirect': '/apply/reset-complete'}, 'org-reset'),
  (r'^apply/reset-complete/?', 'django.contrib.auth.views.password_reset_complete', {'template_name':'grants/password_reset_complete.html'}),

  # fund
  (r'^fund/reset/?$', 'django.contrib.auth.views.password_reset', {'template_name':'fund/reset.html', 'from_email':constants.FUND_EMAIL, 'email_template_name':'fund/password_reset_email.html', 'subject_template_name':'registration/password_reset_subject.txt'}),
  (r'^fund/reset-sent/?', 'django.contrib.auth.views.password_reset_done', {'template_name':'fund/password_reset_done.html'}),
  (r'^fund/reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/?$', 'django.contrib.auth.views.password_reset_confirm', {'template_name':'fund/password_reset_confirm.html', 'post_reset_redirect': '/fund/reset-complete'}, 'fund-reset'),
  (r'^fund/reset-complete/?', 'django.contrib.auth.views.password_reset_complete', {'template_name':'fund/password_reset_complete.html'}),
  )

# GRANTS
urlpatterns += patterns('',
  (r'^apply/nr', direct_to_template, {'template': 'grants/not_grantee.html'}),
  (r'^apply/submitted/?', direct_to_template, {'template': 'grants/submitted.html'}),
  )
urlpatterns += patterns('grants.views',

  (r'^org/?$', 'RedirToApply'),

  #login, logout, registration
  (r'^apply/login/?$', 'OrgLogin'),
  (r'^apply/register/?$', 'OrgRegister'),

  #home page
  (r'^apply/?$','OrgHome'),
  (r'^apply/(?P<draft_id>\d+)/DELETE/?$', 'DiscardDraft'),
  (r'^apply/copy/?$', 'CopyApp'),
  (r'^apply/support/?', 'OrgSupport'),

  #application
  (r'^apply/(?P<cycle_id>\d+)/?$','Apply'),
  (r'^apply/info/(?P<cycle_id>\d+)/?$','PreApply'),

  #application ajax
  (r'^apply/(?P<draft_id>\d+)/add-file/?$', 'AddFile'),
  (r'^get-upload-url/(?P<draft_id>\d+)/?$','RefreshUploadUrl'),
  (r'^apply/(?P<draft_id>\d+)/remove/(?P<file_field>.*)/?$', 'RemoveFile'),
  (r'^apply/(?P<cycle_id>\d+)/autosave/?$','AutoSaveApp'),

  #cron
  (r'^mail/drafts/?', 'DraftWarning'),

  #admin
  (r'^admin/grants/grantapplication/(?P<app_id>\d+)/revert', 'AppToDraft'),
  (r'^admin-advanced/grants/grantapplication/(?P<app_id>\d+)/revert', 'AppToDraft'),
  (r'^admin/grants/grantapplication/(?P<app_id>\d+)/rollover', 'AdminRollover'),
  (r'^admin-advanced/grants/grantapplication/(?P<app_id>\d+)/rollover', 'AdminRollover'),
  (r'^admin/grants/organization/login', 'Impersonate'),

  #reading
  (r'^grants/view/(?P<app_id>\d+)/?$', 'ReadApplication'),
  (r'^grants/view-file/(?P<app_id>\d+)-(?P<file_type>.*)\.', 'ViewFile'),
  (r'^grants/draft-file/(?P<draft_id>\d+)-(?P<file_type>.*)\.', 'ViewDraftFile'),
  (r'^grants/blocked', 'CannotView'),

  #reporting
  (r'^admin/grants/search/?', 'SearchApps'),
  )

# PROJECT CENTRAL
urlpatterns += patterns('fund.views',

  #login, logout, registration
  (r'^fund/login/?$', 'FundLogin'),
  (r'^fund/register/?$', 'Register'),
  (r'^fund/registered/?$', 'Registered'),

  #manage memberships
  (r'^fund/projects/?', 'Projects'),
  (r'^fund/set-current/(?P<ship_id>\d+)/?', 'SetCurrent'),

  #main pages
  (r'^fund/?$', 'Home'),
  (r'^fund/gp/?', 'ProjectPage'),
  (r'^fund/grants/?', 'GrantList'),

  #forms - contacts
  (r'^fund/addmult', 'AddMult'),
  (r'^fund/(?P<donor_id>\d+)/edit','EditDonor'),
  (r'^fund/(?P<donor_id>\d+)/delete', 'DeleteDonor'),
  (r'^fund/add-estimates', 'AddEstimates'),

  #forms - steps
  (r'^fund/(?P<donor_id>\d+)/step$','AddStep'),
  (r'^fund/stepmult$','AddMultStep'),
  (r'^fund/(?P<donor_id>\d+)/(?P<step_id>\d+)$','EditStep'),
  (r'^fund/(?P<donor_id>\d+)/(?P<step_id>\d+)/done','DoneStep'),

  #error/help pages
  (r'^fund/not-member/?', 'NotMember'),
  (r'^fund/pending/?$', 'NotApproved'),
  (r'^fund/support/?', 'Support'),
  (r'^fund/blocked/?$', 'Blocked'),

  #cron
  (r'^mail/overdue-step', 'EmailOverdue'),
  (r'^mail/new-accounts', 'NewAccounts'),
  (r'^mail/gifts', 'GiftNotify'),
  )

#for dev_appserver
urlpatterns += staticfiles_urlpatterns()
