from django import http
from django.shortcuts import render, redirect
from django.template import RequestContext, loader
from google.appengine.api import logservice
import utils
import logging, datetime, csv

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

#logs
def download_logs(request):
  if request.method=='POST':
    form = utils.GaeLogsForm(request.POST)
    if form.is_valid():
      #parse opts
      params = form.cleaned_data
      epoch = datetime.datetime.fromtimestamp(0, params['start'].tzinfo)
      start = params['start'] - epoch
      start = start.total_seconds()
      end = params['end'] - epoch
      end = end.total_seconds()
      #create csv
      response = http.HttpResponse(mimetype='text/plain')
      response['Content-Disposition'] = 'attachment; filename=%s.txt' % 'logs'
      response.write('Logs from ' + str(params['start']) + ' to ' + str(params['end']) + '\n\n')
      for log in logservice.fetch(start_time=start, end_time=end, minimum_log_level=logservice.LOG_LEVEL_DEBUG, include_app_logs=True):
        response.write('\n========== ' + str(log.start_time) + '    ' + log.resource + '    ' +str(log.method) + '    ' + str(log.status) + ' ==========\n\n')
        response.write(str(log.ip) + ' - ' + log.user_agent + '\n')
        response.write('load time: ' + str(log.latency))
        if log.was_loading_request:
          response.write(' (loading request)')
        response.write(', size: ' + str(log.response_size) + ' - referrer: ' + str(log.referrer) + '\n')
        for a in log.app_logs:
          response.write('\n' + str(a.time) + ' level ' + str(a.level) + ': --------\n' + a.message)
        response.write('\n')
      return response
  else:
    form = utils.GaeLogsForm()
  
  return render(request, 'get_logs.html', {'form':form})

def log_javascript(request):
  logging.info('log_js')
  if request.method=='POST':
    logging.warning(request.POST)  
  return http.HttpResponse('success')