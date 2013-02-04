from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.core.urlresolvers import reverse
from django.db import connection
from django.forms.models import model_to_dict
from django.http import HttpResponse, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from google.appengine.ext import blobstore
from grants.forms import *
from grants.decorators import registered_org
import fund, models, datetime, logging, json, re, utils

#ORG VIEWS
def OrgLogin(request):
  error_msg=''
  if request.method=='POST':
    form = LoginForm(request.POST)
    email = request.POST['email'].lower()
    password = request.POST['password']
    user = authenticate(username=email, password=password)
    if user is not None:
      if user.is_active:
        login(request, user)
        return redirect(OrgHome)
      else:
        error_msg='Your account is inactive. Please contact an administrator.'
        logging.warning('Inactive org account tried to log in, username: ' + email)
    else:
      error_msg ="Your password didn't match. Please try again."
  else:
    form = LoginForm()
  register = RegisterForm()
  return render(request, 'grants/org_login.html', {'form':form, 'register':register, 'printout':error_msg})

def OrgRegister(request):
  error_msg=''
  if request.method=='POST':
    register = RegisterForm(request.POST)
    if register.is_valid():
      username_email = request.POST['email'].lower()
      password = request.POST['password']
      org = request.POST['organization']
     
     #check org already registered
      if models.Organization.objects.filter(name=org) or models.Organization.objects.filter(email=username_email):
        error_msg = 'That organization is already registered. Log in instead.'
        logging.warning(org + 'tried to re-register under ' + username_email)
      else:
        #allow existing Users to register as orgs?
        if not User.objects.filter(username=username_email):
          created = User.objects.create_user(username_email, username_email, password)
          logging.info('Created new User ' + username_email)
        user = authenticate(username=username_email, password=password)
        if user:
          if user.is_active:
            login(request, user)
            orgg = models.Organization(name=org, email=username_email)
            orgg.save()
            logging.info('Created new org ' + org)
            return redirect(OrgHome)
          else:
            error_msg='Your account is not active.  Please contact an administrator.'
            logging.error('Inactive acct right after registration, account: ' + username_email)
        else:
          logging.error('Password not working at registration, account:  ' + username_email)
          error_msg='Your password was incorrect.  <a href="/org/support#register-password">More info</a>.'
  else:
    register = RegisterForm()
  form = LoginForm()
  return render(request, 'grants/org_login.html', {'form':form, 'register':register, 'rprintout':error_msg})

@login_required(login_url='/org/login/')
@registered_org()
def OrgHome(request, organization): # /org
    
  saved = models.DraftGrantApplication.objects.filter(organization=organization).select_related('grant_cycle')
  submitted = models.GrantApplication.objects.filter(organization=organization).order_by('-submission_time')
  submitted_cycles = submitted.values_list('grant_cycle', flat=True)
  cycles = models.GrantCycle.objects.filter(close__gt=timezone.now()-datetime.timedelta(days=180)).order_by('open') #grants that closed w/in the last 180 days (~6 mos)
  
  closed = []
  open = []
  applied = []
  upcoming = []
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
  
  return render(request, 'grants/org_home.html', {'user':request.user, 'organization':organization, 'submitted':submitted, 'saved':saved, 'cycles':cycles, 'closed':closed, 'open':open, 'upcoming':upcoming, 'applied':applied})

def OrgSupport(request):
  return render(request, 'grants/org_support.html')
  
@login_required(login_url='/org/login/')
@registered_org()
def Apply(request, organization, cycle_id): # /apply/[cycle_id]
  
  #check cycle exists
  cycle = get_object_or_404(models.GrantCycle, pk=cycle_id)
  
  #check whether cycle is open
  if cycle.is_open()==False: 
    return render(request, 'grants/closed.html', {'cycle':cycle})
  
  #check for app already submitted
  subd = models.GrantApplication.objects.filter(organization=organization, grant_cycle=cycle)
  if subd: 
    return render(request, 'grants/already_applied.html', {'organization':organization, 'cycle':cycle})
  
  if request.method == 'POST':
    post_data = request.POST.copy()
    for key in post_data: #fix newline multiplying
      if key.startswith('_') or key == u'csrfmiddlewaretoken':
          continue
      value = post_data[key]
      if isinstance(value,(str, unicode)):
          post_data[key] = value.replace('\r', '')
    files_data = request.FILES.copy()
    logging.info('FILES at start: ' + str(files_data))
    
    #get or create autosave json, update it from this submission
    dict = json.dumps(post_data)
    saved, cr = models.DraftGrantApplication.objects.get_or_create(organization = organization, grant_cycle=cycle)
    saved.contents = dict
    if files_data.get('budget'): #if new file, use it and save it
      saved.budget = files_data['budget']
    elif saved.budget: #use draft file if it exists
      files_data['budget'] = saved.budget
    if files_data.get('demographics'):
      saved.demographics = files_data['demographics']
    elif saved.demographics:
      files_data['demographics'] = saved.demographics
    if files_data.get('funding_sources'):
      saved.funding_sources = files_data['funding_sources']
    elif saved.funding_sources:
      files_data['funding_sources'] = saved.funding_sources
    if files_data.get('fiscal_letter'):
      saved.fiscal_letter = files_data['fiscal_letter']
    elif saved.fiscal_letter:
      files_data['fiscal_letter'] = saved.fiscal_letter
    saved.save()
    mod = saved.modified
    form = models.GrantApplicationForm(post_data, files_data)
    if form.is_valid():
      logging.info('Application form valid')
      logging.info(request.META['HTTP_REFERER'])
      application = form.save() #save as GrantApp object
      logging.info("Application form saved, budget: " + str(application.budget))
      #update org profile
      form2 = models.OrgProfile(post_data, files_data, instance=organization)
      if form2.is_valid():
        form2.save()
        logging.info('Organization profile updated')
      else:
        logging.error('Application error: profile not updated.  User: %s, application id: %s', request.user.email, application.pk)
      #email confirmation
      subject, from_email = 'Grant application submitted', settings.APP_SEND_EMAIL
      to = organization.email
      html_content = render_to_string('grants/email_submitted.html', {'org':organization, 'cycle':cycle})
      text_content = strip_tags(html_content)
      msg = EmailMultiAlternatives(subject, text_content, from_email, [to], ['sjfnwads@gmail.com'])
      msg.attach_alternative(html_content, "text/html")
      msg.send()
      logging.info("Application created; confirmation email sent to " + to)
      #delete json obj
      saved.delete()
      return redirect('/org/submitted')
    else:
      logging.info("Application form invalid")
      
  else: #GET
    try:
      saved = models.DraftGrantApplication.objects.get(organization=organization, grant_cycle=cycle)
      dict = json.loads(saved.contents)
      logging.debug('Loading draft: ' + str(dict))
      mod = saved.modified
    except models.DraftGrantApplication.DoesNotExist:
      dict = model_to_dict(organization)
      saved = False
      mod = ''
    dict['organization'] = organization
    dict['grant_cycle'] = cycle
    dict['screening_status'] = 10
    form = models.GrantApplicationForm(initial=dict)
  
  #get saved files
  if saved:
    files = {'pk': saved.pk}
    name = str(saved.budget).split('/')[-1]
    files['budget'] = name
    logging.debug('Budget name ' + name)
    name = str(saved.demographics).split('/')[-1]
    files['demographics'] = name
    logging.debug('demographics name ' + name)
    name = str(saved.funding_sources).split('/')[-1]
    files['funding_sources'] = name
    logging.debug('funding_sources name ' + name)
    name = str(saved.fiscal_letter).split('/')[-1]
    files['fiscal_letter'] = name
    logging.info('fiscal_letter name ' + name)
    logging.info('Files dict: ' + str(files))
  else:
    files = ''

  #test replacement: upload_url = '/apply/' + cycle_id + '/'
  upload_url = blobstore.create_upload_url('/apply/' + cycle_id + '/')
  return render(request, 'grants/org_app.html',
  {'form': form, 'cycle':cycle, 'upload_url': upload_url, 'saved':mod, 'limits':models.NARRATIVE_CHAR_LIMITS, 'files':files}  )

@registered_org()
def AutoSaveApp(request, organization, cycle_id):  # /apply/[cycle_id]/autosave/
  
  try:
    cycle = models.GrantCycle.objects.get(pk=cycle_id)
  except models.GrantCycle.DoesNotExist:
    logging.error('Auto-save on cycle that does not exist')
    raise Http404
  
  if request.method == 'POST':
    
    #get or create saved json, update it
    dict = json.dumps(request.POST)
    saved, cr = models.DraftGrantApplication.objects.get_or_create(organization=organization, grant_cycle=cycle)
    saved.contents = dict
    saved.save()
    
    return HttpResponse("")

def AutoSaveFile(request, cycle_id):
  try:
    organization = models.Organization.objects.get(email=request.user.username)
  except models.Organization.DoesNotExist:
    logging.error('Organization not found on file autosave. Email = ' + request.user.username)
    return HttpResponse("Error")
  
  if request.method == 'POST':
    
    saved, cr = models.DraftGrantApplication.objects.get_or_create(organization=organization, grant_cycle=cycle)
    #get file off the request and save it
    return HttpResponse("")

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
    return redirect('/org')
  except models.DraftGrantApplication.DoesNotExist:
    logging.error(str(request.user) + ' discard nonexistent draft')
    raise Http404

def RefreshUploadUrl(request, cycle_id):
  upload_url = blobstore.create_upload_url('/apply/' + cycle_id + '/')
  return HttpResponse(upload_url)

#APPLICATION
def ViewApplication(request, app_id):
  
  user = request.user
  app = get_object_or_404(models.GrantApplication, pk=app_id)
  form = models.GrantApplicationForm(instance = app)
  base_url = settings.APP_BASE_URL
  if not settings.DEBUG:
    base_url = 'https://docs.google.com/viewer?url=' + base_url
  return render(request, 'grants/view_app.html', {'app':app, 'form':form, 'user':user, 'base_url':base_url})

def ViewFile(request, app_id, file_type):
 
  #find the application
  try:
    application = models.GrantApplication.objects.get(pk = app_id)
  except models.GrantApplication.DoesNotExist:
    logging.warning('Grant app not found')
    raise Http404
  
  return utils.FindBlob(application, file_type)

def ViewDraftFile(request, draft_id, file_type): #FINISH
  #find the application
  try:
    application = models.DraftGrantApplication.objects.get(pk = draft_id)
  except models.DraftGrantApplication.DoesNotExist:
    raise Http404('Draft grant app ' + str(draft_id) + ' not found')

  return utils.FindBlob(application, file_type)
    
#REPORTING

#Add your views here.  New views should also be added to urls.py under reporting

#CRON
def DraftWarning(request):
  drafts = models.DraftGrantApplication.objects.all()
  for draft in drafts:
    time_left = draft.grant_cycle.close - timezone.now()
    logging.debug('Time left: ' + str(time_left))
    if datetime.timedelta(days=2) < time_left <= datetime.timedelta(days=3):
      subject, from_email = 'Grant cycle closing soon', settings.APP_SEND_EMAIL
      to = draft.organization.email
      html_content = render_to_string('grants/email_submitted.html', {'org':draft.organization, 'cycle':draft.grant_cycle})
      text_content = strip_tags(html_content)
      msg = EmailMultiAlternatives(subject, text_content, from_email, [to], ['sjfnwads@gmail.com'])
      msg.attach_alternative(html_content, "text/html")
      msg.send()
      logging.info("Email sent to " + to + "regarding draft application soon to expire")
  return HttpResponse("")
  
#DEVEL  
def TestView(request):
  z = timezone.get_default_timezone()
  timezone.activate(z)
  today = timezone.now()
  logging.error('fake test error')
  return render(request, 'debug.html', {'now':today, 'tzzz':z})