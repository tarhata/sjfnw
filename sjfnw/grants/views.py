from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.core.urlresolvers import reverse
from django.db import connection
from django.forms.models import model_to_dict
from django.http import HttpResponse, Http404
from django.shortcuts import render, render_to_response, get_object_or_404, redirect
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from google.appengine.ext import blobstore, deferred
from forms import LoginForm, RegisterForm, RolloverForm, AdminRolloverForm, AppSearchForm, LoginAsOrgForm
from decorators import registered_org
from sjfnw import constants
from sjfnw.fund.models import Member
import models, utils
import datetime, logging, json, re, csv

# CONSTANTS
LOGIN_URL = '/apply/login/'

# PUBLIC ORG VIEWS
def OrgLogin(request):
  login_errors=''
  if request.method=='POST':
    form = LoginForm(request.POST)
    if form.is_valid():
      email = request.POST['email'].lower()
      password = request.POST['password']
      user = authenticate(username=email, password=password)
      if user:
        if user.is_active:
          login(request, user)
          return redirect(OrgHome)
        else:
          login_errors='Your account is inactive. Please contact an administrator.'
          logging.warning('Inactive org account tried to log in, username: ' + email)
      else:
        login_errors ="Your password didn't match. Please try again."
  else:
    form = LoginForm()
  register = RegisterForm()
  return render(request, 'grants/org_login_register.html', {'form':form, 'register':register, 'login_errors':login_errors})

def OrgRegister(request):
  register_error=''
  if request.method=='POST':
    register = RegisterForm(request.POST)
    if register.is_valid():
      username_email = request.POST['email'].lower()
      password = request.POST['password']
      org = request.POST['organization']
      #check org already registered
      if models.Organization.objects.filter(name=org) or models.Organization.objects.filter(email=username_email):
        register_error = 'That organization is already registered. Log in instead.'
        logging.warning(org + 'tried to re-register under ' + username_email)
      #check User already exists, but not as an org
      elif User.objects.filter(username=username_email):
          register_error = 'That email is registered with Project Central. Please register using a different email.'
          logging.warning('User already exists, but not Org: ' + username_email)
      #clear to register
      else:
        #create User and Organization
        created = User.objects.create_user(username_email, username_email, password)
        new_org = models.Organization(name=org, email=username_email)
        new_org.save()
        logging.info('Registration - created user and org for ' + username_email)
        #try to log in
        user = authenticate(username=username_email, password=password)
        if user:
          if user.is_active:
            login(request, user)
            return redirect(OrgHome)
          else:
            register_error='Your account is not active. Please contact an administrator.'
            logging.error('Inactive right after registration, account: ' + username_email)
        else:
          register_error='There was a problem with your registration.  Please <a href=""/apply/support#contact">contact a site admin</a> for assistance.'
          logging.error('Password not working at registration, account:  ' + username_email)
  else: #GET
    register = RegisterForm()
  form = LoginForm()
  return render(request, 'grants/org_login_register.html', {'form':form, 'register':register, 'register_errors':register_error})

def OrgSupport(request):
  return render(request, 'grants/org_support.html', {
  'support_email':constants.SUPPORT_EMAIL,
  'support_form':constants.GRANT_SUPPORT_FORM})

def PreApply(request, cycle_id):
  cycle = get_object_or_404(models.GrantCycle, pk=cycle_id)
  if not cycle.info_page:
    raise Http404
  logging.info(cycle.info_page)
  return render(request, 'grants/pre_apply.html', {'cycle':cycle})

# REGISTERED ORG VIEWS
@login_required(login_url=LOGIN_URL)
@registered_org()
def OrgHome(request, organization):

  saved = models.DraftGrantApplication.objects.filter(organization=organization).select_related('grant_cycle')
  submitted = models.GrantApplication.objects.filter(organization=organization).order_by('-submission_time')
  cycles = models.GrantCycle.objects.filter(close__gt=timezone.now()-datetime.timedelta(days=180)).order_by('open')
  submitted_cycles = submitted.values_list('grant_cycle', flat=True)

  closed, open, applied, upcoming = [], [], [], []
  for cycle in cycles:
    status = cycle.get_status()
    if status=='open':
      if cycle.pk in submitted_cycles:
        applied.append(cycle)
      else:
        open.append(cycle)
    elif status=='closed':
      closed.append(cycle)
    elif status=='upcoming':
      upcoming.append(cycle)
  
  user_override = request.GET.get('user')
  if user_override:
    user_override = '?user=' + user_override
  
  return render(request, 'grants/org_home.html', {
    'organization':organization,
    'submitted':submitted,
    'saved':saved,
    'cycles':cycles,
    'closed':closed,
    'open':open,
    'upcoming':upcoming,
    'applied':applied,
    'user_override':user_override})

@login_required(login_url=LOGIN_URL)
@registered_org()
def Apply(request, organization, cycle_id): # /apply/[cycle_id]
  """Get or submit the whole application form """
  
  #staff override
  user_override = request.GET.get('user')
  if user_override:
    user_override = '?user=' + user_override
    
  #check cycle exists
  cycle = get_object_or_404(models.GrantCycle, pk=cycle_id)

  #check for app already submitted
  if models.GrantApplication.objects.filter(organization=organization, grant_cycle=cycle):
    return render(request, 'grants/already_applied.html', {'organization':organization, 'cycle':cycle})

  #get or create draft
  draft, cr = models.DraftGrantApplication.objects.get_or_create(organization = organization, grant_cycle=cycle)
  profiled = False

  if request.method == 'POST': #POST

    #check if draft can be submitted
    if not draft.editable:
      render(request, 'grants/submitted_closed.html', {'cycle':cycle})
    
    #get fields & files from draft
    draft_data = json.loads(draft.contents)
    logging.debug('draft data: ' + str(draft_data))
    files_data = model_to_dict(draft, fields = draft.file_fields())
    
    #add automated fields
    draft_data['organization'] = organization.pk
    draft_data['grant_cycle'] = cycle.pk

    #create & submit modelform
    form = models.GrantApplicationModelForm(cycle, draft_data, files_data)

    if form.is_valid(): #VALID SUBMISSION
      logging.info('========= Application form valid')
      
      #create the GrantApplication
      new_app = form.save()

      #update org profile
      form2 = models.OrgProfile(draft_data, instance=organization)
      if form2.is_valid():
        form2.save()
        if files_data.get('fiscal_letter'):
          organization.fiscal_letter = files_data['fiscal_letter']
          organization.save()
        logging.info('Organization profile updated')
      else:
        logging.error('Org profile not updated.  User: %s, application id: %s', request.user.email, application.pk)

      #send email confirmation
      subject, from_email = 'Grant application submitted', constants.GRANT_EMAIL
      to = organization.email
      html_content = render_to_string('grants/email_submitted.html', {'org':organization, 'cycle':cycle})
      text_content = strip_tags(html_content)
      msg = EmailMultiAlternatives(subject, text_content, from_email, [to], [constants.SUPPORT_EMAIL])
      msg.attach_alternative(html_content, "text/html")
      msg.send()
      logging.info("Application created; confirmation email sent to " + to)

      #delete draft
      draft.delete()
      
      #success page
      return redirect('/apply/submitted')

    else: #INVALID SUBMISSION
      logging.info("Application form invalid")
      logging.info(form.errors)

  else: #GET

    #get initial data
    if cr or draft.contents=='{}': #load profile
      dict = model_to_dict(organization, exclude = ['fiscal_letter',])
      draft.fiscal_letter = organization.fiscal_letter
      draft.contents = json.dumps(dict)
      draft.save()
      logging.debug('Created new draft')
      if cycle.info_page: #redirect to instructions first
        return render(request, 'grants/pre_apply.html', {'cycle':cycle})

    else: #load a draft
      dict = json.loads(draft.contents)
      timeline = []
      for i in range(15): #covering both timeline formats
        if 'timeline_' + str(i) in dict:
          timeline.append(dict['timeline_' + str(i)])
      dict['timeline'] = json.dumps(timeline)
      logging.debug('Loading draft: ' + str(dict))
    
    #check if draft can be submitted
    if not draft.editable:
      return render(request, 'grants/closed.html', {'cycle':cycle})

    #try to determine initial load - cheaty way
    # 1) if referer, make sure it wasn't from copy 2) check for mission from profile 3) make sure grant request is not there (since it's not in prof)
    referer = request.META.get('HTTP_REFERER')
    if not (referer and referer.find('copy') != -1) and organization.mission and ((not 'grant_request' in dict) or (not dict['grant_request'])):
      profiled = True

    #create form
    form = models.GrantApplicationModelForm(cycle, initial=dict)

  #get draft files
  file_urls = GetFileURLs(draft)
  for field, url in file_urls.iteritems():
    if url:
      name = getattr(draft, field).name.split('/')[-1]
      #short_name = name[:35] + (name[35:] and '..') #stackoverflow'd truncate
      file_urls[field] = '<a href="' + url + '" target="_blank" title="' + name + '">' + name + '</a> [<a onclick="removeFile(\'' + field + '\');">remove</a>]'
    else:
      file_urls[field] = '<i>no file uploaded</i>'

  return render(request, 'grants/org_app.html',
  {'form': form, 'cycle':cycle, 'limits':models.GrantApplication.NARRATIVE_CHAR_LIMITS, 'file_urls':file_urls, 'draft':draft, 'profiled':profiled, 'org':organization, 'user_override':user_override})

def AutoSaveApp(request, cycle_id):  # /apply/[cycle_id]/autosave/
  """ Saves non-file fields to a draft """
  if not request.user.is_authenticated():
    return HttpResponse(LOGIN_URL, status=401)
  username = request.user.username
  if request.user.is_staff and request.GET.get('user'): #staff override
    username = request.GET.get('user')
    logging.info('Staff override - ' + request.user.username + ' logging in as ' + username)
  try:
    organization = models.Organization.objects.get(email=username)
    logging.info(organization)
  except models.Organization.DoesNotExist:
    return HttpResponse('/apply/nr', status=401)

  cycle = get_object_or_404(models.GrantCycle, pk=cycle_id)
  draft = get_object_or_404(models.DraftGrantApplication, organization=organization, grant_cycle=cycle)
  
  if request.method == 'POST':
    #get or create saved json, update it
    logging.debug("Autosaving")
    dict = json.dumps(request.POST)
    logging.debug(dict)
    draft.contents = dict
    draft.modified = timezone.now()
    draft.save()
    return HttpResponse("success")

def AddFile(request, draft_id):
  """ Upload a file to the draft
      Called by javascript in application page """
  
  draft = get_object_or_404(models.DraftGrantApplication, pk=draft_id)
  logging.info([request.body])
  msg = False
  for key in request.FILES:
    if request.FILES[key]:
      logging.info(request.FILES[key])
      if hasattr(draft, key):
        old = getattr(draft, key)
        deferred.defer(utils.DeleteBlob, old)
        setattr(draft, key, request.FILES[key])
        msg = key
        break
      else:
        logging.error('Tried to add an unknown file field ' + str(key))
  draft.modified = timezone.now()
  draft.save()
  logging.info(unicode(draft.organization))
  logging.info(msg)
  if not msg:
    return HttpResponse("ERRORRRRRR")
  name = getattr(draft, msg)
  name = name.name.split('/')[-1]
  
  file_urls = GetFileURLs(draft)
  short_name = name#[:35] + (name[35:] and '..') #stackoverflow'd truncate
  content = msg + u'~~<a href="' + file_urls[msg] + u'" target="_blank" title="' + name + u'">' + short_name + u'</a> [<a onclick="removeFile(\'' + msg + u'\');">remove</a>]'
  logging.info(u"AddFile returning: " + content)
  return HttpResponse(content)

def RemoveFile(request, draft_id, file_field):
  draft = get_object_or_404(models.DraftGrantApplication, pk=draft_id)
  if hasattr(draft, file_field):
    old = getattr(draft, file_field)
    deferred.defer(utils.DeleteBlob, old)
    setattr(draft, file_field, '')
    draft.modified = timezone.now()
    draft.save()
  else:
    logging.error('Tried to remove non-existent field: ' + file_field)
  return HttpResponse('success')
  
def RefreshUploadUrl(request, draft_id):
  """ Get a blobstore url for uploading a file """
  
  #staff override
  user_override = request.GET.get('user')
  if user_override:
    user_override = '?user=' + user_override
  else:
    user_override = ''
    
  upload_url = blobstore.create_upload_url('/apply/' + draft_id + '/add-file' + user_override)
  return HttpResponse(upload_url)

# COPY / DELETE APPS
@login_required(login_url=LOGIN_URL)
@registered_org()
def CopyApp(request, organization):
  
  if request.method == 'POST':
    form = RolloverForm(organization, request.POST)
    if form.is_valid():
      new_cycle = form.cleaned_data.get('cycle')
      draft = form.cleaned_data.get('draft')
      app = form.cleaned_data.get('application')
     
      #get cycle
      try:
        cycle = models.GrantCycle.objects.get(pk = int(new_cycle))
      except models.GrantCycle.DoesNotExist:
        logging.error('CopyApp GrantCycle ' + new_cycle + ' not found')
        return render(request, 'grants/copy_app_error.html')
        
      #make sure the combo does not exist already
      new_draft, cr = models.DraftGrantApplication.objects.get_or_create(organization=organization, grant_cycle=cycle)
      if not cr:
        logging.error("CopyApp the combo already exists!?")
        return render(request, 'grants/copy_app_error.html')
      
      #get app/draft and its contents (json format for draft)
      if app:
        try:
          application = models.GrantApplication.objects.get(pk = int(app))
          content = model_to_dict(application, exclude = application.file_fields() + ['organization', 'grant_cycle', 'submission_time', 'screening_status', 'giving_project', 'scoring_bonus_poc', 'scoring_bonus_geo', 'cycle_question', 'timeline'])
          content.update(dict(zip(['timeline_' + str(i) for i in range(15)], json.loads(application.timeline))))
          content = json.dumps(content)
        except models.GrantApplication.DoesNotExist:
          logging.error('CopyApp - submitted app ' + app + ' not found')
      elif draft:
        try:
          application = models.DraftGrantApplication.objects.get(pk = int(draft))
          content = json.loads(application.contents)
          logging.info(content)
          content['cycle_question'] = ''        
          logging.info(content)
          content = json.dumps(content)
        except models.DraftGrantApplication.DoesNotExist:
          logging.error('CopyApp - draft ' + app + ' not found')
      else:
        logging.error("CopyApp no draft or app...")
        return render(request, 'grants/copy_app_error.html')
      
      #set contents & files
      new_draft.contents = content
      for field in application.file_fields():
        setattr(new_draft, field, getattr(application, field))
      new_draft.save()
      logging.info("CopyApp -- content and files set")
      
      return redirect('/apply/' + new_cycle)

    else: #INVALID FORM
      logging.warning('form invalid')
      cycle_count = str(form['cycle']).count('<option value')
      apps_count = str(form['application']).count('<option value') + str(form['draft']).count('<option value')
  
  else: #GET
    form = RolloverForm(organization)
    cycle_count = str(form['cycle']).count('<option value')
    apps_count = str(form['application']).count('<option value') + str(form['draft']).count('<option value')
    logging.info(cycle_count)
    logging.info(apps_count)    
  
  return render(request, 'grants/org_app_copy.html', {'form':form, 'cycle_count':cycle_count, 'apps_count':apps_count})
    
@registered_org()
def DiscardDraft(request, organization, draft_id):

  #look for saved draft
  try:
    saved = models.DraftGrantApplication.objects.get(pk = draft_id)
    if saved.organization == organization:
      saved.delete()
      logging.info('Draft ' + str(draft_id) + ' discarded')
    else: #trying to delete another person's draft!?
      logging.warning('Failed attempt to discard draft ' + str(draft_id) + ' by ' + str(organization))
    return redirect(OrgHome)
  except models.DraftGrantApplication.DoesNotExist:
    logging.error(str(request.user) + ' discard nonexistent draft')
    raise Http404

# VIEW APPS/FILES

def view_permission(user, application):
  """ Return a number indicating viewing permission for a submitted app.
      
      Args:
        user: django user object
        application: GrantApplication
      
      Returns:
        0 - does not have permission to view
        1 - member with perm
        2 - staff
        3 - app creator
  """
  if user.is_staff:
    return 2
  elif user.email == application.organization.email:
    return 3
  else:
    try:
      member = Member.objects.select_related().get(email=user.email)
      for ship in member.membership_set.all():
        if ship.giving_project == application.giving_project:
          return 1
      return 0
    except Member.DoesNotExist:
      return 0

def CannotView(request):
  return render(request, 'grants/blocked.html', {'contact_url':'/support#contact'})

@login_required(login_url=LOGIN_URL)
def ReadApplication(request, app_id):
  user = request.user
  app = get_object_or_404(models.GrantApplication, pk=app_id)
  perm = view_permission(user, app)
  logging.info('perm is ' + str(perm))
  if perm == 0:
    return redirect(CannotView)
  form = models.GrantApplicationModelForm(app.grant_cycle)
  file_urls = GetFileURLs(app)
  
  return render(request, 'grants/reading.html', {'app':app, 'form':form, 'user':user, 'file_urls':file_urls, 'perm':perm})

def ViewFile(request, app_id, file_type):
  application =  get_object_or_404(models.GrantApplication, pk = app_id)
  return utils.ServeBlob(application, file_type)

def ViewDraftFile(request, draft_id, file_type):
  application =  get_object_or_404(models.DraftGrantApplication, pk = draft_id)
  return utils.ServeBlob(application, file_type)

# ADMIN
def RedirToApply(request):
  return redirect('/apply/')

def AppToDraft(request, app_id):

  submitted_app = get_object_or_404(models.GrantApplication, pk = app_id)
  organization = submitted_app.organization
  grant_cycle = submitted_app.grant_cycle

  if request.method == 'POST':
    #create draft from app
    draft = models.DraftGrantApplication(organization = organization, grant_cycle = grant_cycle)
    content = model_to_dict(submitted_app, exclude = submitted_app.file_fields() + ['organization', 'grant_cycle', 'submission_time', 'screening_status', 'giving_project', 'scoring_bonus_poc', 'scoring_bonus_geo', 'timeline'])
    content.update(dict(zip(['timeline_' + str(i) for i in range(15)], json.loads(submitted_app.timeline))))
    draft.contents = json.dumps(content)
    for field in submitted_app.file_fields():
      setattr(draft, field, getattr(submitted_app, field))
    draft.modified = timezone.now()
    draft.save()
    logging.info('Reverted to draft, draft id ' + str(draft.pk))
    #delete app
    submitted_app.delete()
    #redirect to draft page
    return redirect('/admin/grants/draftgrantapplication/'+str(draft.pk)+'/')
  #GET
  return render(request, 'admin/grants/confirm_revert.html', {'application':submitted_app})

def AdminRollover(request, app_id):
  application = get_object_or_404(models.GrantApplication, pk = app_id)
  org = application.organization
  
  if request.method=='POST':
    form = AdminRolloverForm(org, request.POST)
    if form.is_valid():
      cycle = get_object_or_404(models.GrantCycle, pk = int(form.cleaned_data['cycle']))
      logging.info("Success rollover of " + unicode(application) + ' to ' + str(cycle))
      application.pk = None
      application.screening_status = 10
      application.submission_time = timezone.now()
      application.grant_cycle = cycle
      application.giving_project = None
      application.save()
      return redirect('/admin/grants/grantapplication/'+str(application.pk)+'/')
  else:
    form = AdminRolloverForm(org)
    cycle_count = str(form['cycle']).count('<option value')
    
  return render(request, 'admin/grants/rollover.html', {'form':form, 'application':application, 'count':cycle_count})

def Impersonate(request):
  
  if request.method=='POST':
    form = LoginAsOrgForm(request.POST)
    if form.is_valid():
      org = form.cleaned_data['organization']
      return redirect('/apply/?user='+org)
  form = LoginAsOrgForm()
  return render(request, 'admin/grants/impersonate.html', {'form':form})
  
def SearchApps(request):
  form = AppSearchForm()
  
  if request.method=='POST':
    logging.info('Search form submitted')
    form = AppSearchForm(request.POST)
    
    if form.is_valid():
      logging.info('A valid form')
      
      options = form.cleaned_data
      logging.info(options)
      apps = models.GrantApplication.objects.order_by('-submission_time').select_related('giving_project', 'grant_cycle')
      
      #filters
      min_year = datetime.datetime.strptime(options['year_min'] + '-01-01 00:00:01', '%Y-%m-%d %H:%M:%S') 
      min_year = timezone.make_aware(min_year, timezone.get_current_timezone())
      max_year = datetime.datetime.strptime(options['year_max'] + '-12-31 23:59:59', '%Y-%m-%d %H:%M:%S') 
      max_year = timezone.make_aware(max_year, timezone.get_current_timezone())
      apps = apps.filter(submission_time__gte=min_year, submission_time__lte=max_year)
      logging.info('After year, count is ' + str(apps.count()))
      if options.get('organization'):
        apps = apps.filter(organization__contains=options['organization'])
      if options.get('city'):
        apps = apps.filter(city=options['city'])
      if options.get('state'):
        apps = apps.filter(state__in=options['state'])
      if options.get('screening_status'):
        apps = apps.filter(screening_status__in=options.get('screening_status'))
      logging.info('After screening status, count is ' + str(apps.count()))
      if options.get('poc_bonus'):
        apps = apps.filter(scoring_bonus_poc=True)
      if options.get('geo_bonus'):
        apps = apps.filter(scoring_bonus_geo=True)
      if options.get('giving_project'):
        apps = apps.filter(giving_project__title__in=options.get('giving_project'))
      logging.info('After gp, count is ' + str(apps.count()))
      if options.get('grant_cycle'):
        apps = apps.filter(grant_cycle__title__in=options.get('grant_cycle'))
      logging.info('After cycle, count is ' + str(apps.count()))
      
      #fields
      fields = ['submission_time', 'organization', 'grant_cycle'] + options['report_basics'] + options['report_contact'] + options['report_org'] + options['report_proposal'] + options['report_budget']
      if options['report_fiscal']:
        fields += models.GrantApplication.fiscal_fields()
      if options['report_collab']:
        fields += [f for f in filter(lambda x: x.startswith('collab_ref'), models.GrantApplication._meta.get_all_field_names())]
      if options['report_racial_ref']:
        fields += [f for f in filter(lambda x: x.startswith('racial_justice'), models.GrantApplication._meta.get_all_field_names())]
      if options['report_bonuses']:
        fields.append('scoring_bonus_poc')
        fields.append('scoring_bonus_geo')
      
      #get results
      results = get_results(fields, apps)
      fields = [f.capitalize().replace('_', ' ') for f in fields] #for display
      
      #format results
      if options['format']=='browse':
        return render_to_response('grants/report_results.html', {'results':results, 'fields':fields})
      elif options['format']=='csv':
        response = HttpResponse(mimetype='text/csv')
        response['Content-Disposition'] = 'attachment; filename=%s.csv' % 'grantapplications'
        writer = csv.writer(response)
        writer.writerow(fields)
        for row in results:
          writer.writerow(row)
        return response
    else:
      logging.info('Invalid form!')  
  return render(request, 'grants/search_applications.html', {'form':form})

def get_results(fields, apps):
  """ Return a list of lists.  Each list represents an app, contains selected field values
      
      Arguments:
        fields - list of fields to include
        apps - queryset of applications """
        
  results = []
  for app in apps:
    row = []
    for field in fields:
      if field=='screening_status':
        val = getattr(app, field)
        if val:
          convert = dict(models.GrantApplication.SCREENING_CHOICES)
          val = convert[val]
        row.append(val)
      else:
        row.append(getattr(app, field))
    results.append(row)
  logging.info(results)
  
  return results

# CRON
def DeleteEmptyFiles(request): #/tools/delete-empty
  """ Delete all 0kb files in the blobstore """
  infos = blobstore.BlobInfo.all().filter('size =', 0)
  count = 0
  for i in infos:
    count += 1
    i.delete()
  logging.info('Deleted ' + str(count) + 'empty files.')
  return HttpResponse("done")

def DraftWarning(request):
  """ Warns of impending draft freeze
  Do not change cron sched -- it depends on running only once/day
  7 day warning if created 7+ days before close, otherwise 3 day warning """
  
  drafts = models.DraftGrantApplication.objects.all()
  now = timezone.now()
  eight = datetime.timedelta(days=8)
  
  for draft in drafts:
    time_left = draft.grant_cycle.close - timezone.now()
    created_offset = draft.grant_cycle.close - draft.created
    if (created_offset > eight and eight > time_left > datetime.timedelta(days=7)) or (created_offset < eight and datetime.timedelta(days=2) < time_left <= datetime.timedelta(days=3)):
      subject, from_email = 'Grant cycle closing soon', constants.GRANT_EMAIL
      to = draft.organization.email
      html_content = render_to_string('grants/email_draft_warning.html', {'org':draft.organization, 'cycle':draft.grant_cycle})
      text_content = strip_tags(html_content)
      msg = EmailMultiAlternatives(subject, text_content, from_email, [to], [constants.SUPPORT_EMAIL])
      msg.attach_alternative(html_content, "text/html")
      msg.send()
      logging.info("Email sent to " + to + "regarding draft application soon to expire")
  return HttpResponse("")

# UTILS (caused import probs in utils.py)
def GetFileURLs(app):
  """ Given a draft or application
  return a dict of urls for viewing each of its files
  taking into account whether it can be viewed in google doc viewer """
    
  #determine whether draft or submitted
  if isinstance(app, models.GrantApplication):
    mid_url = 'grants/view-file/'
  elif isinstance(app, models.DraftGrantApplication):
    mid_url = 'grants/draft-file/'
  else:
    logging.error("GetFileURLs received invalid object")
    return {}
  
  #check file fields, compile links
  file_urls = {'budget': '', 'funding_sources':'', 'demographics':'', 'fiscal_letter':'', 'budget1': '', 'budget2': '', 'budget3': '', 'project_budget_file': ''}
  for field in file_urls:
    value = getattr(app, field)
    if value:
      ext = value.name.lower().split(".")[-1]
      file_urls[field] += settings.APP_BASE_URL + mid_url + str(app.pk) + u'-' + field + u'.' + ext
      if not settings.DEBUG and ext in constants.VIEWER_FORMATS: #doc viewer
        file_urls[field] = 'https://docs.google.com/viewer?url=' + file_urls[field] + '&embedded=true'
  return file_urls