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

# PUBLIC ORG VIEWS
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

def OrgSupport(request):
  return render(request, 'grants/org_support.html', {
  'support_email':settings.SUPPORT_EMAIL,
  'support_form':settings.SUPPORT_FORM_URL})

# REGISTERED ORG VIEWS
@login_required(login_url='/org/login/')
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

@login_required(login_url='/org/login/')
@registered_org()
def Apply(request, organization, cycle_id): # /apply/[cycle_id]
  
  #check cycle exists
  cycle = get_object_or_404(models.GrantCycle, pk=cycle_id)

  #check for app already submitted
  if models.GrantApplication.objects.filter(organization=organization, grant_cycle=cycle):
    return render(request, 'grants/already_applied.html', {'organization':organization, 'cycle':cycle})
  
  #get or create draft
  saved, cr = models.DraftGrantApplication.objects.get_or_create(organization = organization, grant_cycle=cycle)
  
  #check if draft can be submitted
  if not saved.editable: 
    return render(request, 'grants/closed.html', {'cycle':cycle})

  if request.method == 'POST': #POST
    
    #fix newline multiplying
    post_data = request.POST.copy()
    
    #debug
    
    logging.info("Start of POST:")
    logz = "1: " + str(post_data.get('narrative1') or 'empty')
    logz = logz.replace("\r", "<r>")
    logz = logz.replace("\n", "<n>")
    logging.info(logz)
    logz = "2: " + str(post_data.get('narrative2') or 'empty')
    logz = logz.replace("\r", "<r>")
    logz = logz.replace("\n", "<n>")
    logging.info(logz)
    logz = "3: " + str(post_data.get('narrative3') or 'empty')
    logz = logz.replace("\r", "<r>")
    logz = logz.replace("\n", "<n>")
    logging.info(logz)
    
    for key in post_data:
      if key.startswith('_') or key == u'csrfmiddlewaretoken':
        continue
      value = post_data[key]
      if isinstance(value,(str, unicode)):
        post_data[key] = value.replace('\r', '')
    
    logging.info("After newline sub")
    logz = "1: " + str(post_data.get('narrative1') or 'empty')
    logz = logz.replace("\r", "<r>")
    logz = logz.replace("\n", "<n>")
    logging.info(logz)
    logz = "2: " + str(post_data.get('narrative2') or 'empty')
    logz = logz.replace("\r", "<r>")
    logz = logz.replace("\n", "<n>")
    logging.info(logz)
    logz = "3: " + str(post_data.get('narrative3') or 'empty')
    logz = logz.replace("\r", "<r>")
    logz = logz.replace("\n", "<n>")
    logging.info(logz)
    
    #update draft from this submission
    dict = json.dumps(post_data)
    saved.contents = dict
    
    #update draft files or pull them into the post
    files_data = request.FILES.copy()
    logging.debug('FILES at start: ' + str(files_data.lists()))
    if files_data.get('budget'):
      logging.debug('budget in POST, saving to draft: ' + str(files_data['budget']))
      saved.budget = files_data['budget']
    elif saved.budget:
      files_data['budget'] = saved.budget
    if files_data.get('demographics'):
      logging.debug('demo in POST, saving to draft')
      saved.demographics = files_data['demographics']
    elif saved.demographics:
      files_data['demographics'] = saved.demographics
    if files_data.get('funding_sources'):
      logging.debug('funding in POST, saving to draft')
      saved.funding_sources = files_data['funding_sources']
    elif saved.funding_sources:
      files_data['funding_sources'] = saved.funding_sources
    if files_data.get('fiscal_letter'):
      logging.debug('fiscal in POST, saving to draft')
      saved.fiscal_letter = files_data['fiscal_letter']
    elif saved.fiscal_letter:
      files_data['fiscal_letter'] = saved.fiscal_letter
    saved.save()
    mod = saved.modified
    
    #submit form
    logging.info('Submitting files_data: ' + str(files_data.lists()))
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
      saved.delete()
      
      return redirect('/org/submitted')
    
    else: #INVALID SUBMISSION
      logging.info("Application form invalid")
      logging.info(form.errors)
      
  else: #GET
    
    #get initial data
    if cr: #load profile
      dict = model_to_dict(organization)
      saved.fiscal_letter = organization.fiscal_letter
      saved.contents = dict
      saved.save()
      logging.debug('Created new draft')
      mod = ''   
    else: #load a draft
      dict = json.loads(saved.contents)
      logging.debug('Loading draft: ' + str(dict))
      mod = saved.modified
    
    #fill in fkeys TODO handle this on post
    dict['organization'] = organization
    dict['grant_cycle'] = cycle
    dict['screening_status'] = 10
    
    #create form
    form = models.GrantApplicationForm(initial=dict)
  
  #get saved files
  files = {'pk': saved.pk}
  name = str(saved.budget).split('/')[-1]
  files['budget'] = name
  name = str(saved.demographics).split('/')[-1]
  files['demographics'] = name
  name = str(saved.funding_sources).split('/')[-1]
  files['funding_sources'] = name
  name = str(saved.fiscal_letter).split('/')[-1]
  files['fiscal_letter'] = name
  logging.info('Files dict: ' + str(files))
  file_urls = utils.GetFileURLs(saved)
  
  #upload url
  #test replacement:  upload_url = '/apply/' + cycle_id + '/'
  #live:  
  upload_url = blobstore.create_upload_url('/apply/' + cycle_id + '/')
  
  return render(request, 'grants/org_app.html',
  {'form': form, 'cycle':cycle, 'upload_url': upload_url, 'saved':mod, 'limits':models.NARRATIVE_CHAR_LIMITS, 'files':files, 'file_urls':file_urls})

@registered_org()
def AutoSaveApp(request, organization, cycle_id):  # /apply/[cycle_id]/autosave/
  
  try:
    cycle = models.GrantCycle.objects.get(pk=cycle_id)
  except models.GrantCycle.DoesNotExist:
    logging.error('Auto-save on cycle that does not exist')
    raise Http404
  
  if request.method == 'POST':
    #get or create saved json, update it
    logging.info("Autosaving")
    logz = "1: " + str(request.POST.get('narrative1') or 'empty')
    logz = logz.replace("\r", "<r>")
    logz = logz.replace("\n", "<n>")
    logging.info(logz)
    logz = "2: " + str(request.POST.get('narrative2') or 'empty')
    logz = logz.replace("\r", "<r>")
    logz = logz.replace("\n", "<n>")
    logging.info(logz)
    logz = "3: " + str(request.POST.get('narrative3') or 'empty')
    logz = logz.replace("\r", "<r>")
    logz = logz.replace("\n", "<n>")
    logging.info(logz)
    dict = json.dumps(request.POST)
    saved, cr = models.DraftGrantApplication.objects.get_or_create(organization=organization, grant_cycle=cycle)
    saved.contents = dict
    saved.save()   
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

# VIEW APPS/FILES
def ViewApplication(request, app_id): 
  user = request.user
  app = get_object_or_404(models.GrantApplication, pk=app_id)
  form = models.GrantApplicationForm(instance = app)
  #set up doc viewer for applicable files
  file_urls = utils.GetFileURLs(app)
  
  return render(request, 'grants/view_app.html', {'app':app, 'form':form, 'user':user, 'file_urls':file_urls})

def ViewFile(request, app_id, file_type):
 
  #find the application
  try:
    application = models.GrantApplication.objects.get(pk = app_id)
  except models.GrantApplication.DoesNotExist:
    logging.warning('Grant app not found')
    raise Http404
  
  return utils.FindBlob(application, file_type)

def ViewDraftFile(request, draft_id, file_type):
  #find the application
  try:
    application = models.DraftGrantApplication.objects.get(pk = draft_id)
  except models.DraftGrantApplication.DoesNotExist:
    raise Http404('Draft grant app ' + str(draft_id) + ' not found')

  return utils.FindBlob(application, file_type)

# ADMIN
def AppToDraft(request, app_id):
  
  submitted_app = get_object_or_404(models.GrantApplication, pk = app_id).select_related('organization', 'grant_cycle')
  organization = submitted_app.organization
  grant_cycle = submitted_app.grant_cycle
  
  if request.method == 'POST':
    #create draft from app
    draft = models.DraftGrantApplication(organization = organization, grant_cycle = grant_cycle)
    content = model_to_dict(submitted_app, exclude = ['budget', 'demographics', 'funding_sources', 'fiscal_letter', 'submission_time', 'screening_status', 'giving_project', 'scoring_bonus_poc', 'scoring_bonus_geo'])
    draft.contents = content
    draft.budget = submitted_app.budget
    draft.demographics = submitted_app.demographics
    draft.fiscal_letter = submitted_app.fiscal_letter
    draft.funding_sources = submitted_app.funding_sources
    draft.save()
    logging.info('Reverted to draft, draft id ' + str(draft.pk))
    #email notification to org TODO replace template
    html_content = render_to_string('grants/email_submitted.html', {'org':organization, 'cycle':grant_cycle, 'submission':submitted_app.submission_time})
    text_content = strip_tags(html_content)
    msg = EmailMultiAlternatives('Submitted application re-opened for edits', text_content, settings.GRANT_EMAIL, [organization.email], [settings.SUPPORT_EMAIL])
    msg.attach_alternative(html_content, "text/html")
    #delete app
    submitted_app.delete()
    msg.send()
    logging.info("Email sent to " + to + "regarding draft application re-opened")
    #redirect to draft page
    return redirect('/admin/grants/draftgrantapplication/'+str(draft.pk)+'/')
  #GET
  return render(request, 'admin/grants/confirm_revert.html', {'application':submitted_app})

# CRON
def DraftWarning(request):
  drafts = models.DraftGrantApplication.objects.all()
  for draft in drafts:
    time_left = draft.grant_cycle.close - timezone.now()
    logging.debug('Time left: ' + str(time_left))
    if datetime.timedelta(days=2) < time_left <= datetime.timedelta(days=3):
      subject, from_email = 'Grant cycle closing soon', settings.GRANT_EMAIL
      to = draft.organization.email
      html_content = render_to_string('grants/email_draft_warning.html', {'org':draft.organization, 'cycle':draft.grant_cycle})
      text_content = strip_tags(html_content)
      msg = EmailMultiAlternatives(subject, text_content, from_email, [to], [settings.SUPPORT_EMAIL])
      msg.attach_alternative(html_content, "text/html")
      msg.send()
      logging.info("Email sent to " + to + "regarding draft application soon to expire")
  return HttpResponse("")