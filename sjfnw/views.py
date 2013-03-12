from django import http
from django.shortcuts import redirect
from django.template import RequestContext, loader
import logging

#404
def page_not_found(request):
  """ Modified version of default handler - returns app-specific template. 
    Needs to give template: title_addition, contact_url """
  path = request.path
  if path.find('/fund') == 0:
    title_addition = ' - Project Central'
    contact_url = '/fund/support'
  elif path.find('/org') == 0 or  path.find('/apply') == 0:
    title_addition = ' - Social Justice Fund Grants'
    contact_url = '/org/support'
  else:
    title_addition = ' - Social Justice Fund Apps'
    contact_url = False
  template_name = '404.html'
  t = loader.get_template(template_name)
  return http.HttpResponseNotFound(t.render(RequestContext(request, {'title_addition': title_addition, 'contact_url':contact_url})))
  
#500
def server_error(request):
  """ Modified version of default handler - returns app-specific template. 
    Needs to give template: title_addition, contact_url """
  path = request.path
  if path.find('/fund') == 0:
    title_addition = ' - Project Central'
    contact_url = '/fund/support'
  elif path.find('/org') == 0 or  path.find('/apply') == 0:
    title_addition = ' - Social Justice Fund Grants'
    contact_url = '/org/support'
  else:
    title_addition = ' - Social Justice Fund Apps'
    contact_url = False
  template_name = '500.html'
  t = loader.get_template(template_name)
  return http.HttpResponseNotFound(t.render(RequestContext(request, {'title_addition': title_addition, 'contact_url':contact_url})))

#admin -> admin/
def admin_redirect(request):
  return redirect('/admin/')

#admin-advanced -> admin-advanced/
def admin_adv_redirect(request):
  return redirect('/admin-advanced/')