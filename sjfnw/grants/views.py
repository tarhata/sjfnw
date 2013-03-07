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
from forms import LoginForm, RegisterForm, RolloverForm, GrantApplicationFormy
from decorators import registered_org
from sjfnw import fund
import models, utils
import datetime, logging, json, re, quopri

# CONSTANTS
LOGIN_URL = '/apply/login/'
APP_FILE_FIELDS = ['budget', 'demographics', 'funding_sources', 'fiscal_letter', 'budget1', 'budget2', 'budget3', 'project_budget_file']

# PUBLIC ORG VIEWS
def OrgLogin(request):
  login_errors=''
  if request.method=='POST':
    form = LoginForm(request.POST)
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
            error_msg='Your account is not active. Please contact an administrator.'
            logging.error('Inactive right after registration, account: ' + username_email)
        else:
          error_msg='There was a problem with your registration.  Please <a href=""/apply/support#contact">contact a site admin</a> for assistance.'
          logging.error('Password not working at registration, account:  ' + username_email)
  else: #GET
    register = RegisterForm()
  form = LoginForm()
  return render(request, 'grants/org_login_register.html', {'form':form, 'register':register, 'register_errors':register_errors})

def OrgSupport(request):
  return render(request, 'grants/org_support.html', {
  'support_email':settings.SUPPORT_EMAIL,
  'support_form':settings.SUPPORT_FORM_URL})

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

  return render(request, 'grants/org_home.html', {
    'organization':organization,
    'submitted':submitted,
    'saved':saved,
    'cycles':cycles,
    'closed':closed,
    'open':open,
    'upcoming':upcoming,
    'applied':applied})

#@login_required(login_url=LOGIN_URL)
#@registered_org()
def PreApply(request, cycle_id):
  cycle = get_object_or_404(models.GrantCycle, pk=cycle_id)
  if not cycle.info_page:
    raise Http404
  logging.info(cycle.info_page)
  return render(request, 'grants/pre_apply.html', {'cycle':cycle})

@login_required(login_url=LOGIN_URL)
@registered_org()
def Apply(request, organization, cycle_id): # /apply/[cycle_id]
  """Get or submit the whole application form """
  
  referer = request.META.get('HTTP_REFERER')
  logging.info(referer)
  
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
    #get files from draft
    files_data = model_to_dict(draft, fields = ['fiscal_letter', 'budget', 'demographics', 'funding_sources'])
    
    #get other fields from draft
    post_data = json.loads(draft.contents)
    
    #set the auto fields
    post_data['organization'] = organization.pk
    post_data['grant_cycle'] = cycle.pk
    post_data['screening_status'] = 10
    logging.info(post_data)
    
    #submit form
    form = models.GrantApplicationForm(post_data, files_data)

    if form.is_valid(): #VALID SUBMISSION
      logging.info('Application form valid')

      #save as GrantApplication object
      application = form.save()

      #update org profile
      form2 = models.OrgProfile(post_data, instance=organization)
      if form2.is_valid():
        form2.save()
        if files_data.get('fiscal_letter'):
          organization.fiscal_letter = files_data['fiscal_letter']
          organization.save()
        logging.info('Organization profile updated')
      else:
        logging.error('Org profile not updated.  User: %s, application id: %s', request.user.email, application.pk)

      #send email confirmation
      subject, from_email = 'Grant application submitted', settings.GRANT_EMAIL
      to = organization.email
      html_content = render_to_string('grants/email_submitted.html', {'org':organization, 'cycle':cycle})
      text_content = strip_tags(html_content)
      msg = EmailMultiAlternatives(subject, text_content, from_email, [to], [settings.SUPPORT_EMAIL])
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
    if cr: #load profile
      dict = model_to_dict(organization, exclude = ['fiscal_letter',])
      draft.fiscal_letter = organization.fiscal_letter
      draft.contents = json.dumps(dict)
      draft.save()
      logging.debug('Created new draft')
      if cycle.info_page: #redirect to instructions first
        return render(request, 'grants/pre_apply.html', {'cycle':cycle})

    else: #load a draft
      dict = json.loads(draft.contents)
      logging.debug('Loading draft: ' + str(dict))
    
    #check if draft can be submitted
    if not draft.editable:
      return render(request, 'grants/closed.html', {'cycle':cycle})

    #try to determine initial load - cheaty way
    if not referer.find('copy') != -1 and organization.mission and ((not 'grant_request' in dict) or (not dict['grant_request'])):
      profiled = True
    
    #fill in fkeys TODO handle this on post
    dict['organization'] = organization
    dict['grant_cycle'] = cycle
    dict['screening_status'] = 10

    #create form
    form = models.GrantApplicationForm(initial=dict)

  #get draft files
  file_urls = utils.GetFileURLs(draft)
  for field, url in file_urls.iteritems():
    if url:
      name = str(getattr(draft, field)).split('/')[-1]
      short_name = name[:40] + (name[40:] and '..') #stackoverflow'd truncate
      file_urls[field] = '<a href="' + url + '" target="_blank" title="' + name + '">' + short_name + '</a>'
    else:
      file_urls[field] = '<i>no file uploaded</i>'

  return render(request, 'grants/org_app.html',
  {'form': form, 'cycle':cycle, 'limits':models.NARRATIVE_CHAR_LIMITS, 'file_urls':file_urls, 'draft':draft, 'profiled':profiled})

def TestApply(request):
  form = GrantApplicationFormy()
  return render(request, 'grants/file_upload.html', {'form':form})

@login_required(login_url=LOGIN_URL)
@registered_org()
def AutoSaveApp(request, organization, cycle_id):  # /apply/[cycle_id]/autosave/
  """ Saves non-file fields to a draft """
  
  cycle = get_object_or_404(models.GrantCycle, pk=cycle_id)
  
  if request.method == 'POST':
    #get or create saved json, update it
    logging.debug("Autosaving")
    dict = json.dumps(request.POST)
    saved, cr = models.DraftGrantApplication.objects.get_or_create(organization=organization, grant_cycle=cycle)
    saved.contents = dict
    saved.save()
    return HttpResponse("")

def AddFile(request, draft_id):
  """ Upload a file (saves to draft, included when submitting)
    Template needs: link domain, draft pk, field name or id, file name """
  draft = get_object_or_404(models.DraftGrantApplication, pk=draft_id)
  logging.info('AddFile called: ' + str(request.FILES.lists()))
  msg = False
  for key in request.FILES:
    if request.FILES[key]:
      setattr(draft, key, request.FILES[key])
      msg = key
      break
  draft.save()
  if not msg:
    return HttpResponse("ERRORRRRRR")
  name = getattr(draft, msg)
  name = str(name).split('/')[-1]
  
  file_urls = utils.GetFileURLs(draft)
  content = msg + '~~<a href="' + file_urls[msg] + '" target="_blank">' + name + '</a>'
  logging.info("AddFile returning: " + content)
  return HttpResponse(content)

def RefreshUploadUrl(request, draft_id):
  """ Get a blobstore url for uploading a file """
  upload_url = blobstore.create_upload_url('/apply/' + draft_id + '/add-file')
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

      #get app/draft and its contents (json format for draft)
      if app:
        try:
          application = models.GrantApplication.objects.get(pk = int(app))
          content = json.dumps(model_to_dict(application, exclude = APP_FILE_FIELDS + ['grant_cycle', 'submission_time', 'screening_status', 'giving_project', 'scoring_bonus_poc', 'scoring_bonus_geo', 'cycle_question']))
        except models.GrantApplication.DoesNotExist:
          logging.error('CopyApp - submitted app ' + app + ' not found')
      elif draft:
        try:
          application = models.DraftGrantApplication.objects.get(pk = int(draft))
          content = application.contents
          logging.info(content)
          if content['cycle_question']:
            logging.info('Removing extra q')
            content['cycle_question'] = ''
          logging.info(content)
        except models.DraftGrantApplication.DoesNotExist:
          logging.error('CopyApp - draft ' + app + ' not found')
      else:
        logging.error("CopyApp no draft or app...")
      
      #make sure the combo does not exist already
      new_draft, cr = models.DraftGrantApplication.objects.get_or_create(organization=organization, grant_cycle=cycle)
      if not cr:
        logging.error("CopyApp the combo already exists!?")
        return HttpResponse("Error")
      
      #set contents & files
      new_draft.contents = content
      for field in APP_FILE_FIELDS:
        setattr(new_draft, field, getattr(application, field))
      new_draft.save()
      logging.info("CopyApp -- content and files set")
      
      return redirect('/apply/' + new_cycle)

    else: #INVALID FORM
      logging.warning('form invalid')
  
  else: #GET
    form = RolloverForm(organization)
    cycle_count = str(form['cycle']).count('<option value')
    apps_count = str(form['application']).count('<option value') + str(form['draft']).count('<option value')
    logging.info(cycle_count)
    logging.info(apps_count)    
  
  return render(request, 'grants/org_app_copy.html', {'form':form, 'cycle_count':cycle_count, 'apps_count':apps_count})

def DiscardFile(request, filefield):
  """ Takes the string stored in the django file field
    Queues file for deletion """
  pass
    
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
def ViewApplication(request, app_id):
  user = request.user
  app = get_object_or_404(models.GrantApplication, pk=app_id)
  form = models.GrantApplicationForm(instance = app)
  #set up doc viewer for applicable files
  file_urls = utils.GetFileURLs(app)

  return render(request, 'grants/view_app.html', {'app':app, 'form':form, 'user':user, 'file_urls':file_urls})

def ViewFile(request, app_id, file_type):
  application =  get_object_or_404(models.GrantApplication, pk = app_id)
  return utils.FindBlob(application, file_type)

def ViewDraftFile(request, draft_id, file_type):
  application =  get_object_or_404(models.DraftGrantApplication, pk = draft_id)
  return utils.FindBlob(application, file_type)

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
    draft.contents = json.dumps(model_to_dict(submitted_app, exclude = APP_FILE_FIELDS + ['grant_cycle', 'submission_time', 'screening_status', 'giving_project', 'scoring_bonus_poc', 'scoring_bonus_geo']))
    draft.budget = submitted_app.budget
    draft.demographics = submitted_app.demographics
    draft.fiscal_letter = submitted_app.fiscal_letter
    draft.funding_sources = submitted_app.funding_sources
    draft.save()
    logging.info('Reverted to draft, draft id ' + str(draft.pk))
    #delete app
    submitted_app.delete()
    #redirect to draft page
    return redirect('/admin/grants/draftgrantapplication/'+str(draft.pk)+'/')
  #GET
  return render(request, 'admin/grants/confirm_revert.html', {'application':submitted_app})

# CRON
def DraftWarning(request):
  """ Warns of impending draft freeze
  Do not change cron sched -- it depends on running only once/day
  7 day warning if created 7+ days before close, otherwise 3 day warning """
  
  drafts = models.DraftGrantApplication.objects.all()
  now = timezone.now()

  for draft in drafts:
    time_left = draft.grant_cycle.close - timezone.now()
    created_offset = draft.grant_cycle.close - draft.created
    if (created_offset > eight and eight > time_left > datetime.timedelta(days=7)) or (created_offset < eight and datetime.timedelta(days=2) < time_left <= datetime.timedelta(days=3)):
      subject, from_email = 'Grant cycle closing soon', settings.GRANT_EMAIL
      to = draft.organization.email
      html_content = render_to_string('grants/email_draft_warning.html', {'org':draft.organization, 'cycle':draft.grant_cycle})
      text_content = strip_tags(html_content)
      msg = EmailMultiAlternatives(subject, text_content, from_email, [to], [settings.SUPPORT_EMAIL])
      msg.attach_alternative(html_content, "text/html")
      msg.send()
      logging.info("Email sent to " + to + "regarding draft application soon to expire")
  return HttpResponse("")