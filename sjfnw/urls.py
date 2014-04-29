from django.conf.urls import patterns, include
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic.base import TemplateView

from sjfnw.admin import advanced_admin
from sjfnw.grants.urls import apply_urls, report_urls, grants_urls, root_urls

handler404 = 'sjfnw.views.page_not_found'
handler500 = 'sjfnw.views.server_error'

admin.autodiscover() # load admin.py from all apps

urlpatterns = patterns('',
  (r'^/?$', TemplateView.as_view(template_name='home.html')),

  # project central
  (r'^fund$', 'sjfnw.fund.views.home'),
  (r'^fund/', include('sjfnw.fund.urls')),
  (r'^fund/logout/?$', 'django.contrib.auth.views.logout', {'next_page': '/fund'}),

  # grants
  (r'^apply/?', include(apply_urls)),
  (r'^grants/?', include(grants_urls)),
  (r'^report/', include(report_urls)),
  (r'^', include(root_urls)),
  (r'^org/?$', 'sjfnw.grants.views.RedirToApply'),
  (r'^logout/?$', 'django.contrib.auth.views.logout', {'next_page': '/apply'}),
  (r'^get-upload-url/?','sjfnw.grants.views.RefreshUploadUrl'), #TODO put this under /apply

  # admin
  (r'^admin/', include(admin.site.urls)),
  (r'^admin$', 'sjfnw.views.admin_redirect'),
  (r'^admin-advanced/', include(advanced_admin.urls)),
  (r'^admin-advanced$', 'sjfnw.views.admin_adv_redirect'),
  (r'^admin/grants/grantapplication/(?P<app_id>\d+)/revert', 'sjfnw.grants.views.AppToDraft'),
  (r'^admin-advanced/grants/grantapplication/(?P<app_id>\d+)/revert', 'sjfnw.grants.views.AppToDraft'),
  (r'^admin/grants/grantapplication/(?P<app_id>\d+)/rollover', 'sjfnw.grants.views.AdminRollover'),
  (r'^admin-advanced/grants/grantapplication/(?P<app_id>\d+)/rollover', 'sjfnw.grants.views.AdminRollover'),
  (r'^admin/grants/organization/login', 'sjfnw.grants.views.Impersonate'),
  (r'^admin/grants/organization/(?P<org_id>\d+)/update', 'sjfnw.grants.views.update_profile'),

  #reporting
  (r'^admin/grants/search/?', 'sjfnw.grants.views.grants_report'),

  # cron emails
  (r'^mail/overdue-step', 'sjfnw.fund.views.email_overdue'),
  (r'^mail/new-accounts', 'sjfnw.fund.views.new_accounts'),
  (r'^mail/gifts', 'sjfnw.fund.views.gift_notify'),
  (r'^mail/drafts/?', 'sjfnw.grants.views.DraftWarning'),

  # dev
  (r'^dev/jslog/?', 'sjfnw.views.log_javascript'),
  (r'^dev/donor-dups', 'sjfnw.fund.views.find_duplicates'),
)

#for dev_appserver
urlpatterns += staticfiles_urlpatterns()

