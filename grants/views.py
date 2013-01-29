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
import fund, models, datetime, logging, json, re

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

def OrgRegister(request): #update - uses old try/catch instead of filters
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
          logging.error('Password not working right after registration, account:  ' + username_email)
          error_msg="Your password was incorrect.  Try again."
  else:
    register = RegisterForm()
  form = LoginForm()
  return render(request, 'grants/org_login.html', {'form':form, 'register':register, 'rprintout':error_msg})

@login_required(login_url='/org/login/')
def OrgHome(request): # /org
  try:
    grantee = models.Organization.objects.get(email=request.user.username)
  except models.Organization.DoesNotExist:
    return redirect('/org/nr')
    
  saved = models.DraftGrantApplication.objects.filter(organization=grantee).select_related('grant_cycle')
  submitted = models.GrantApplication.objects.filter(organization=grantee).order_by('-submission_time')

  cycles = models.GrantCycle.objects.filter(close__gt=timezone.now()-datetime.timedelta(days=180)).order_by('open') #grants that closed w/in the last 180 days (~6 mos)
  
  closed = []
  open = []
  upcoming = []
  for cycle in cycles:
    status = cycle.get_status()
    if status=='open':
      open.append(cycle)
    elif status=='closed':
      closed.append(cycle)
    elif status=='upcoming':
      upcoming.append(cycle)
  
  return render(request, 'grants/org_home.html', {'user':request.user, 'grantee':grantee, 'submitted':submitted, 'saved':saved, 'cycles':cycles, 'closed':closed, 'open':open, 'upcoming':upcoming})

def OrgSupport(request):
  return render(request, 'grants/org_support.html')
  
@login_required(login_url='/org/login/')
def Apply(request, cycle_id): # /apply/[cycle_id]
  
  #check that user is registered as an org
  try: 
    grantee = models.Organization.objects.get(email=request.user.username)
  except models.Organization.DoesNotExist:
    return redirect('/org/nr')
  
  #check cycle exists
  cycle = get_object_or_404(models.GrantCycle, pk=cycle_id)
  
  #check whether cycle is open
  if cycle.is_open()==False: 
    return render(request, 'grants/closed.html', {'cycle':cycle})
  
  #check for app already submitted
  subd = models.GrantApplication.objects.filter(organization=grantee, grant_cycle=cycle)
  if subd: 
    return render(request, 'grants/already_applied.html', {'grantee':grantee, 'cycle':cycle})
  
  if request.method == 'POST':
    post_data = request.POST.copy()
    for key in post_data: #fix newline multiplying
      if key.startswith('_') or key == u'csrfmiddlewaretoken':
          continue
      value = post_data[key]
      if isinstance(value,(str, unicode)):
          post_data[key] = value.replace('\r', '')
    form = models.GrantApplicationForm(post_data, request.FILES)
    logging.info("Application POST, files:" + str(request.FILES))
    #get or create autosave json, update it **UPDATE**
    dict = json.dumps(post_data)
    saved, cr = models.DraftGrantApplication.objects.get_or_create(organization = grantee, grant_cycle=cycle)
    saved.contents = dict
    saved.file1 = request.FILES['budget']
    saved.save()
    mod = saved.modified
    if form.is_valid():
      logging.info('Application form valid')
      logging.info(request.META['HTTP_REFERER'])
      application = form.save() #save as GrantApp object
      if application.fiscal_letter:
        application.fiscal_letter_type = str(application.fiscal_letter).split('.')[-1]
        application.fiscal_letter_name = str(application.submission_time.year)+str(application.organization)+'FiscalLetter.'+application.fiscal_letter_type
        application.fiscal_letter_name = application.fiscal_letter_name.replace(' ', '')
      application.save()
      logging.info("Application form saved, budget: " + str(application.budget))
      #update org profile
      form2 = models.OrgProfile(request.POST, instance=grantee)
      if form2.is_valid():
        form2.save()
        logging.info('Organization profile updated')
      else:
        logging.error('Application error: profile not updated.  User: %s, application id: %s', request.user.email, application.pk)
      #email confirmation
      subject, from_email = 'Grant application submitted', settings.APP_SEND_EMAIL
      to = grantee.email
      html_content = render_to_string('grants/email_submitted.html', {'org':grantee, 'cycle':cycle})
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
      saved = models.DraftGrantApplication.objects.get(organization=grantee, grant_cycle=cycle)
      dict = json.loads(saved.contents)
      logging.info(dict)
      mod = saved.modified
    except models.DraftGrantApplication.DoesNotExist:
      dict = model_to_dict(grantee)
      mod = ''
    dict['organization'] = grantee
    dict['grant_cycle'] = cycle
    dict['screening_status'] = 10
    form = models.GrantApplicationForm(initial=dict)
    files = {'budget': saved.file1}
  #file upload prep
  #view_url = reverse('grants.views.Apply', args=(cycle_id,)) #current url
  #upload_url, blah = prepare_upload(request, view_url)
  upload_url = blobstore.create_upload_url('/apply/' + cycle_id + '/')
  #logging.info('Upload prepped, url: ' + upload_url)
  
  return render(request, 'grants/org_app.html',
  {'form': form, 'cycle':cycle, 'upload_url': upload_url, 'saved':mod, 'limits':models.NARRATIVE_CHAR_LIMITS, 'files':files}  )

def AutoSaveApp(request, cycle_id):  # /apply/[cycle_id]/autosave/
  try:
    grantee = models.Organization.objects.get(email=request.user.username)
  except models.Organization.DoesNotExist:
    return redirect('/org/nr')
  
  try:
    cycle = models.GrantCycle.objects.get(pk=cycle_id)
  except models.GrantCycle.DoesNotExist:
    logging.error('Auto-save on cycle that does not exist')
    raise Http404
  
  if request.method == 'POST':
    
    #get or create saved json, update it
    dict = json.dumps(request.POST)
    saved, cr = models.DraftGrantApplication.objects.get_or_create(organization=grantee, grant_cycle=cycle)
    saved.contents = dict
    saved.save()
    
    return HttpResponse("")

def AutoSaveFile(request, cycle_id):
  try:
    grantee = models.Organization.objects.get(email=request.user.username)
  except models.Organization.DoesNotExist:
    logging.error('Organization not found on file autosave. Email = ' + request.user.username)
    return HttpResponse("Error")
  
  if request.method == 'POST':
    
    saved, cr = models.DraftGrantApplication.objects.get_or_create(organization=grantee, grant_cycle=cycle)
    #get file off the request and save it
    return HttpResponse("")

def DiscardDraft(request, cycle_id):
  try:
    grantee = models.Organization.objects.get(email=request.user.username)
  except models.Organization.DoesNotExist:
    return redirect('/org/nr')
  
  try:
    cycle = models.GrantCycle.objects.get(pk=cycle_id)
  except models.GrantCycle.DoesNotExist:
    logging.error(str(request.user) + ' discard nonexistent cycle ' + str(cycle_id))
    raise Http404
  
  #look for saved draft
  try:
    saved = models.DraftGrantApplication.objects.get(organization=grantee, grant_cycle=cycle)
    saved.delete()
    return redirect('/org')
  except models.DraftGrantApplication.DoesNotExist:
    logging.error(str(request.user) + ' discard nonexistent draft, cycle ' + str(cycle_id))
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
  
  #find the file
  if file_type == 'budget':
    file_field = application.budget
  elif file_type == 'demographics':
    file_field = application.demographics
  elif file_type == 'funding':
    file_field = application.funding_sources
  else:
    logging.warning('Unknown file type ' + file_type)
    raise Http404
  
  #filefield stores key that gets us the blobinfo
  blobinfo_key = str(file_field).split('/', 1)[0]
  blobinfo = blobstore.BlobReader(blobinfo_key).readlines()
  #look through the info for the creation time of the blob
  blobinfo_dict =  dict([l.split(': ', 1) for l in blobinfo if l.strip()])
  creation_time = blobinfo_dict['X-AppEngine-Upload-Creation'].strip()
  
  if not settings.DEBUG: #convert to datetime for live
    creation_time = datetime.datetime.strptime(creation_time, '%Y-%m-%d %H:%M:%S.%f')
    creation_time = timezone.make_aware(creation_time, timezone.get_current_timezone())
  
  logging.info('Looking for: ' + str(creation_time))
  
  #find blob that matches the creation time
  for b in  blobstore.BlobInfo.all():    
    c = b.creation
    if settings.DEBUG: #local - just compare strings
      if str(timezone.localtime(c)) == creation_time:
        return HttpResponse(blobstore.BlobReader(b).read(), content_type=b.content_type)
    else:
      c = timezone.make_aware(c, timezone.utc)
      if timezone.localtime(c) == creation_time:
        return HttpResponse(blobstore.BlobReader(b).read(), content_type=b.content_type)
  logging.info('No match, raising 404')
  raise Http404

def ViewDraftFile(request, draft_id, file_type): #FINISH
  #find the application
  try:
    application = models.GrantApplication.objects.get(pk = app_id)
  except models.GrantApplication.DoesNotExist:
    logging.warning('Grant app not found')
    raise Http404

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