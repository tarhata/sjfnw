from django import http
from django.template import RequestContext, loader
import logging

#404
def page_not_found(request):
  """ Modified version of default handler - returns app-specific template. 
    Needs to give template: title_addition, contact_url """
  path = request.path
  logging.info(path)
  if path.find('/fund') == 0:
    logging.info('404 in fund app')
    title_addition = ' - Project Central'
    contact_url = '/fund/support'
  elif path.find('/org') == 0 or  path.find('/apply') == 0:
    logging.info('404 in grant org app')
    title_addition = ' - SJF Grants'
    contact_url = '/org/support'
  else:
    logging.info('404 generic')
    title_addition = ' - SJF Apps'
    contact_url = False
  template_name = '404.html'
  t = loader.get_template(template_name)
  return http.HttpResponseNotFound(t.render(RequestContext(request, {'title_addition': title_addition, 'contact_url':contact_url})))
  
#500
def server_error(request):
  """ Modified version of default handler - returns app-specific template. 
    Needs to give template: title_addition, contact_url """
  path = request.path
  logging.info(path)
  if path.find('/fund') == 0:
    logging.info('500 in fund app')
    title_addition = ' - Project Central'
    contact_url = '/fund/support'
  elif path.find('/org') == 0 or  path.find('/apply') == 0:
    logging.info('500 in grant org app')
    title_addition = ' - SJF Grants'
    contact_url = '/org/support'
  else:
    logging.info('500 generic')
    title_addition = ' - SJF Apps'
    contact_url = False
  template_name = '500.html'
  t = loader.get_template(template_name)
  return http.HttpResponseNotFound(t.render(RequestContext(request, {'title_addition': title_addition, 'contact_url':contact_url})))