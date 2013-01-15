from django import http, template, forms
from django.db import IntegrityError
from django.forms.models import model_to_dict
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.http import HttpResponseServerError, HttpResponse, Http404
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.urlresolvers import reverse
import fund, models, datetime, logging
import json as simplejson
from grants.forms import *
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from django.core.files.uploadhandler import FileUploadHandler
from django.conf import settings
from djangoappengine import storage

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
  return render_to_response('grants/org_login.html', {'form':form, 'register':register, 'printout':error_msg})

def OrgRegister(request): #update - uses old try/catch instead of filters
  error_msg=''
  if request.method=='POST':
    register = RegisterForm(request.POST)
    if register.is_valid():
      username_email = request.POST['email'].lower()
      password = request.POST['password']
      org = request.POST['organization']
     
     #check org already registered
      if models.Grantee.objects.filter(name=org) or models.Grantee.objects.filter(email=username_email):
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
            orgg = models.Grantee(name=org, email=username_email)
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
  return render_to_response('grants/org_login.html', {'form':form, 'register':register, 'rprintout':error_msg})

@login_required(login_url='/org/login/')
def OrgHome(request): # /org
  try:
    grantee = models.Grantee.objects.get(email=request.user.username)
  except models.Grantee.DoesNotExist:
    return redirect('/org/nr')
    
  saved = models.SavedGrantApplication.objects.filter(organization=grantee)
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
  
  return render_to_response('grants/org_home.html', {'user':request.user,'grantee':grantee,'submitted':submitted,'saved':saved, 'cycles':cycles, 'closed':closed, 'open':open, 'upcoming':upcoming})

def OrgSupport(request):
  if request.user:
    member = request.user #for shared template
  return render_to_response('grants/org_support.html', {'grantee':member})
  
@login_required(login_url='/org/login/')
def Apply(request, cycle_id): # /apply/[cycle_id]

  #check that user is registered as an org
  try: 
    grantee = models.Grantee.objects.get(email=request.user.username)
  except models.Grantee.DoesNotExist:
    return redirect('/org/nr')
  
  #check cycle exists
  cycle = get_object_or_404(models.GrantCycle, pk=cycle_id)
  
  #check whether cycle is open
  if cycle.is_open()==False: 
    return render_to_response('grants/closed.html', {'cycle':cycle})
  
  #check for app already submitted
  subd = models.GrantApplication.objects.filter(organization=grantee, grant_cycle=cycle)
  if subd: 
    return render_to_response('grants/already_applied.html', {'grantee':grantee, 'cycle':cycle})  
  
  #get narrative text overrides if they exist
  try: 
    texts = models.NarrativeText.objects.get(name="Application")
  except models.NarrativeText.DoesNotExist:
    texts = None
  
  if request.method == 'POST':
    form = models.GrantApplicationForm(request.POST, request.FILES)
    logging.info("Application POST, files:" + str(request.FILES))
    #get or create autosave json, update it **UPDATE**
    dict = simplejson.dumps(request.POST)
    saved, cr = models.SavedGrantApplication.objects.get_or_create(organization = grantee, grant_cycle=cycle)
    saved.contents = dict
    saved.save()
    mod = saved.modified

    if form.is_valid():
      logging.info("Application form valid")
      application = form.save() #save as GrantApp object
      """might need a name storage field?
      application.file1_name = str(application.submission_time)+str(application.organization)+'.'+application.file1_type
      application.file1_name = application.file1_name.replace(' ', '')
      """
      if application.fiscal_letter:
        application.fiscal_letter_type = str(application.fiscal_letter).split('.')[-1]
        application.fiscal_letter_name = str(application.submission_time.year)+str(application.organization)+'FiscalLetter.'+application.fiscal_letter_type
        application.fiscal_letter_name = application.fiscal_letter_name.replace(' ', '')
      application.save()
      logging.info("Application form saved, file1: " + str(application.file1))
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
      return redirect('/org/submitted.html')
    else:
      logging.info("Application form invalid: " + str(form.errors))
  else: #GET
    try:
      saved = models.SavedGrantApplication.objects.get(organization=grantee, grant_cycle=cycle)
      dict = simplejson.loads(saved.contents)
      mod = saved.modified
    except models.SavedGrantApplication.DoesNotExist:
      dict = model_to_dict(grantee)
      mod = ''
    dict['organization'] = grantee
    dict['grant_cycle'] = cycle
    dict['screening_status'] = 10
    form = models.GrantApplicationForm(initial=dict)
  
  #file upload prep
  #view_url = reverse('grants.views.Apply', args=(cycle_id,)) #current url
  #upload_url, blah = prepare_upload(request, view_url)
  upload_url = blobstore.create_upload_url('/apply/' + cycle_id + '/')
  logging.info('Upload prepped, url: ' + upload_url)
  
  return render_to_response('grants/org_app.html',
  {'grantee':grantee, 'form': form, 'cycle':cycle, 'upload_url': upload_url, 'texts':texts, 'saved':mod}  )

def AutoSaveApp(request, cycle_id):  # /apply/[cycle_id]/autosave/
  try:
    grantee = models.Grantee.objects.get(email=request.user.username)
  except models.Grantee.DoesNotExist:
    return redirect('/org/nr')
  
  try:
    cycle = models.GrantCycle.objects.get(pk=cycle_id)
  except models.GrantCycle.DoesNotExist:
    logging.error('Auto-save on cycle that does not exist')
    return redirect('/org')
  
  if request.method == 'POST':
    
    #get or create saved json, update it
    dict = simplejson.dumps(request.POST)
    saved, cr = models.SavedGrantApplication.objects.get_or_create(organization=grantee, grant_cycle=cycle)
    saved.contents = dict
    saved.save()
    
    return HttpResponse("")

def AutoSaveFile(request, cycle_id):
  try:
    grantee = models.Grantee.objects.get(email=request.user.username)
  except models.Grantee.DoesNotExist:
    logging.error('Grantee not found on file autosave. Email = ' + request.user.username)
    return HttpResponse("Error")
  
  if request.method == 'POST':
    
    saved, cr = models.SavedGrantApplication.objects.get_or_create(organization=grantee, grant_cycle=cycle)
    #get file off the request and save it
    return HttpResponse("")

def DiscardDraft(request, cycle_id):
  try:
    grantee = models.Grantee.objects.get(email=request.user.username)
  except models.Grantee.DoesNotExist:
    return redirect('/org/nr')
  
  try:
    cycle = models.GrantCycle.objects.get(pk=cycle_id)
  except models.GrantCycle.DoesNotExist:
    return redirect('/org')
  
  #look for saved draft
  try:
    saved = models.SavedGrantApplication.objects.get(organization=grantee, grant_cycle=cycle)
    saved.delete()
    return redirect('/org')
  except models.SavedGrantApplication.DoesNotExist:
    return redirect('/org')

#APPLICATION
def view_app(request, app_id):
  user = request.user
  app = get_object_or_404(models.GrantApplication, pk=app_id)
  form = models.GrantApplicationForm(instance = app)
  return render_to_response('grants/view_app.html', {'app':app, 'form':form, 'user':user})

def download_handler(request, app_id, file_type):
  logging.info('download_handler called, file_type: ' + file_type)
  #return serve_file(request, key)
  try:
    upload = models.GrantApplication.objects.get(pk = app_id)
    logging.info('Trying to serve ' + str(upload.file1))
    #logging.info('.key is ' + str(upload.file1.key()))
  except models.GrantApplication.DoesNotExist:
    logging.warning('Grant app not found')
    raise Http404
  #import pdb; pdb.set_trace()
  
  blobinfo_key = str(upload.file1).split('/', 1)[0]
  blobinfo = blobstore.BlobReader(blobinfo_key).readlines()
  
  blobinfo_dict =  dict([l.split(': ', 1) for l in blobinfo if l.strip()])
  creation_time = blobinfo_dict['X-AppEngine-Upload-Creation'].strip()
  logging.info(creation_time)
  
  for b in  blobstore.BlobInfo.all():    
    if str(b.creation) == creation_time:
      return HttpResponse(blobstore.BlobReader(b).read(), content_type=b.content_type)
  raise Http404('How could this possibly have gone wrong?')
  
  """
  if b.key() == "tQcX6YOnvYIehiMThLMdBOrKCVNOiPdHUtD2KMAbaVWNEdlV29Vn0UcAbp7v6dGR":
    print "".join(b.open().readlines())

    creation_time =  dict([l.split(': ', 1) for l in b.open().readlines() if l.strip()])['X-AppEngine-Upload-Creation']
  #break

  for b in  blobstore.BlobInfo.all():
    print b.creation, creation_time
    #if b.creation == creation_time:
    #  print "win"
    
  # blob_reader = blobstore.BlobReader()
  """

  return storage.serve_file(request, upload.file1, None, None)
  
#REPORTING

#Add your views here.  New views should also be added to urls.py under reporting

#CRON
def DraftWarning(request):
  drafts = models.SavedGrantApplication.objects.all()
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
  return render_to_response('debug.html', {'now':today, 'tzzz':z})