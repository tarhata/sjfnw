from django.conf.urls import patterns
from sjfnw import constants

urlpatterns = patterns('sjfnw.fund.views',

  #login, logout, registration
  (r'^login/?$', 'fund_login'),
  (r'^register/?$', 'fund_register'),
  (r'^registered/?$', 'registered'),

  #main pages
  (r'^$', 'home'),
  (r'^gp/?', 'project_page'),
  (r'^grants/?', 'grant_list'),

  #manage memberships
  (r'^projects/?', 'manage_account'),
  (r'^set-current/(?P<ship_id>\d+)/?', 'set_current'),

  #forms - contacts
  (r'^add-contacts', 'add_mult'),
  (r'^(?P<donor_id>\d+)/edit','edit_donor'),
  (r'^(?P<donor_id>\d+)/delete', 'delete_donor'),
  (r'^add-estimates', 'add_estimates'),
  (r'^copy', 'copy_contacts'),

  #forms - steps
  (r'^(?P<donor_id>\d+)/step$','add_step'),
  (r'^stepmult$','add_mult_step'),
  (r'^(?P<donor_id>\d+)/(?P<step_id>\d+)$','edit_step'),
  (r'^(?P<donor_id>\d+)/(?P<step_id>\d+)/done','done_step'),

  #error/help pages
  (r'^not-member/?', 'not_member'),
  (r'^pending/?$', 'not_approved'),
  (r'^support/?', 'support'),
  (r'^blocked/?$', 'blocked'),
)

urlpatterns += patterns('',
  # password reset
  (r'^reset/?$', 'django.contrib.auth.views.password_reset', {'template_name':'fund/reset.html', 'from_email':constants.FUND_EMAIL, 'email_template_name':'fund/password_reset_email.html', 'subject_template_name':'registration/password_reset_subject.txt'}),
  (r'^reset-sent/?$', 'django.contrib.auth.views.password_reset_done', {'template_name':'fund/password_reset_done.html'}),
  (r'^reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/?$', 'django.contrib.auth.views.password_reset_confirm', {'template_name':'fund/password_reset_confirm.html', 'post_reset_redirect': '/fund/reset-complete'}, 'fund-reset'),
  (r'^reset-complete/?$', 'django.contrib.auth.views.password_reset_complete', {'template_name':'fund/password_reset_complete.html'}),
)

