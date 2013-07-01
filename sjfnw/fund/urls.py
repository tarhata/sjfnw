from django.conf.urls import patterns
from sjfnw import constants

urlpatterns = patterns('fund.views',

  #login, logout, registration
  (r'^login/?$', 'FundLogin'),
  (r'^register/?$', 'Register'),
  (r'^registered/?$', 'Registered'),

  #main pages
  (r'^$', 'Home'),
  (r'^gp/?', 'ProjectPage'),
  (r'^grants/?', 'GrantList'),

  #manage memberships
  (r'^projects/?', 'Projects'),
  (r'^set-current/(?P<ship_id>\d+)/?', 'SetCurrent'),

  #forms - contacts
  (r'^addmult', 'AddMult'),
  (r'^(?P<donor_id>\d+)/edit','EditDonor'),
  (r'^(?P<donor_id>\d+)/delete', 'DeleteDonor'),
  (r'^add-estimates', 'AddEstimates'),

  #forms - steps
  (r'^(?P<donor_id>\d+)/step$','AddStep'),
  (r'^stepmult$','AddMultStep'),
  (r'^(?P<donor_id>\d+)/(?P<step_id>\d+)$','EditStep'),
  (r'^(?P<donor_id>\d+)/(?P<step_id>\d+)/done','DoneStep'),

  #error/help pages
  (r'^not-member/?', 'NotMember'),
  (r'^pending/?$', 'NotApproved'),
  (r'^support/?', 'Support'),
  (r'^blocked/?$', 'Blocked'),
)

urlpatterns += patterns('',
  # password reset
  (r'^reset/?$', 'django.contrib.auth.views.password_reset', {'template_name':'fund/reset.html', 'from_email':constants.FUND_EMAIL, 'email_template_name':'fund/password_reset_email.html', 'subject_template_name':'registration/password_reset_subject.txt'}),
  (r'^reset-sent/?$', 'django.contrib.auth.views.password_reset_done', {'template_name':'fund/password_reset_done.html'}),
  (r'^reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/?$', 'django.contrib.auth.views.password_reset_confirm', {'template_name':'fund/password_reset_confirm.html', 'post_reset_redirect': '/fund/reset-complete'}, 'fund-reset'),
  (r'^reset-complete/?$', 'django.contrib.auth.views.password_reset_complete', {'template_name':'fund/password_reset_complete.html'}),
)

