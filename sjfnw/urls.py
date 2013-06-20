from django.conf.urls import patterns, include
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from sjfnw.admin import advanced_admin
import views
from grants.urls import apply_urls, grants_urls

handler404 = 'views.page_not_found'
handler500 = 'views.server_error'

admin.autodiscover() # load admin.py from all apps

urlpatterns = patterns('',
  (r'^/?$', 'django.views.generic.simple.direct_to_template', {'template': 'home.html'}),

  # project central
  (r'^fund/?', include('sjfnw.fund.urls')),
  (r'^fund/logout/?$', 'django.contrib.auth.views.logout', {'next_page': '/fund'}),

  # grants
  (r'^apply/?', include(apply_urls)),
  (r'^grants/?', include(grants_urls)),
  (r'^org/?$', 'sjfnw.grants.views.RedirToApply'),
  (r'^logout/?$', 'django.contrib.auth.views.logout', {'next_page': '/apply'}),
  (r'^get-upload-url/(?P<draft_id>\d+)/?$','sjfnw.grants.views.RefreshUploadUrl'), #TODO put this under /apply

  # admin
  (r'^admin/', include(admin.site.urls)),
  (r'^admin$', views.admin_redirect),
  (r'^admin-advanced/', include(advanced_admin.urls)),
  (r'^admin-advanced$', views.admin_adv_redirect),
  (r'^admin/grants/grantapplication/(?P<app_id>\d+)/revert', 'sjfnw.grants.views.AppToDraft'),
  (r'^admin-advanced/grants/grantapplication/(?P<app_id>\d+)/revert', 'sjfnw.grants.views.AppToDraft'),
  (r'^admin/grants/grantapplication/(?P<app_id>\d+)/rollover', 'sjfnw.grants.views.AdminRollover'),
  (r'^admin-advanced/grants/grantapplication/(?P<app_id>\d+)/rollover', 'sjfnw.grants.views.AdminRollover'),
  (r'^admin/grants/organization/login', 'sjfnw.grants.views.Impersonate'),
  #reporting
  (r'^admin/grants/search/?', 'sjfnw.grants.views.SearchApps'),

  # cron emails
  (r'^mail/overdue-step', 'sjfnw.fund.views.EmailOverdue'),
  (r'^mail/new-accounts', 'sjfnw.fund.views.NewAccounts'),
  (r'^mail/gifts', 'sjfnw.fund.views.GiftNotify'),
  (r'^mail/drafts/?', 'sjfnw.grants.views.DraftWarning'),

  # dev
  (r'^dev/jslog/?', 'views.log_javascript'),
  )


#for dev_appserver
urlpatterns += staticfiles_urlpatterns()

