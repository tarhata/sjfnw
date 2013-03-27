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
      response = http.HttpResponse(mimetype='text/csv')
      response['Content-Disposition'] = 'attachment; filename=%s.csv' % 'logs'
      writer = csv.writer(response)
      writer.writerow(['request id', 'version', 'start time', 'end time', 'resource', 'ip', 'host', 'latency', 'method', 'referrer', 'response size', 'task queue name', 'user agent',' loading'])
      for log in logservice.fetch(start_time=start, end_time=end, minimum_log_level=logservice.LOG_LEVEL_DEBUG, include_app_logs=True):
        writer.writerow([log.request_id, log.version_id, log.start_time, log.end_time, log.resource, log.ip, log.host, log.latency, log.method, log.referrer, log.response_size, log.task_queue_name, log.user_agent, log.was_loading_request])
        for a in log.app_logs:
          writer.writerow([log.request_id, a.time, a.level, a.message])
      return response
  else:
    form = utils.GaeLogsForm()
  
  return render(request, 'get_logs.html', {'form':form})