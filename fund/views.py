from django import http, template, forms
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.db import IntegrityError, connection
from django.db.models import Sum, Count, Avg, Min, Max
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.forms.formsets import formset_factory
from django.utils import timezone
import models, datetime, random, logging
import json as simplejson
import grants.models
from fund.decorators import approved_membership
from fund.forms import *
import scoring.models
import pytz
from google.appengine.ext import deferred, ereporter
import utils

if not settings.DEBUG:
  ereporter.register_logger()

#LOGIN & REGISTRATION
def FundLogin(request):
  printout=''
  if request.method=='POST':
    form = LoginForm(request.POST)
    username = request.POST['email'].lower()
    password = request.POST['password']
    user = authenticate(username=username, password=password)
    if user is not None:
        if user.is_active:
            login(request, user)
            return redirect(Home)
        else:
            printout='Your account is not active.  Contact an administrator.'
            logging.warning("Inactive account tried to log in. Username: "+username)
    else:
        printout ="Your login and password didn't match."
  else:
    form = LoginForm()
  return render_to_response('fund/login.html', {'form':form, 'printout':printout})

def Register(request):
  printout = ''
  if request.method=='POST':
    register = RegistrationForm(request.POST)
    if register.is_valid():
      username = request.POST['email'].lower()
      password = request.POST['password']
      if User.objects.filter(username=username):
        printout = 'That email is already registered.  <a href="/fund/login/">Login</a> instead.'
        logging.info('Email already registered: ' + username)
      else:
        created = User.objects.create_user(username, username, password)
        created.save()
        fn = request.POST['first_name']
        ln = request.POST['last_name']
        gp = request.POST['giving_project']
        member, cr = models.Member.objects.get_or_create(email=username, defaults = {'first_name':fn, 'last_name':ln})
        if cr:
          logging.info('Registration - user and member objects created for '+username)
        else:
          logging.info(username + ' registered as User, Member object already existed')
        if gp:
          giv = models.GivingProject.objects.get(pk=gp)
          membership, crs = models.Membership.objects.get_or_create(member = member, giving_project = giv)
          member.current = membership.pk
          member.save()
          logging.info('Registration - membership in ' + str(giv) + ' or marked as current')
        user = authenticate(username=username, password=password)
        if user:
          if user.is_active:
            login(request, user)
            return redirect('/fund/registered')
          else: #not active
            printout = 'There was a problem with your registration.  Please contact a site admin for assistance.'
            logging.error('Inactive right after registering. Email: ' + username)
        else: #email & pw didn't match
          printout = 'There was a problem with your registration.  Please contact a site admin for assistance.'
          logging.error("Password didn't match right after registering. Email: " + username)
  else:
    register = RegistrationForm()
    
  return render_to_response('fund/register.html', {'form':register, 'printout':printout})

@login_required(login_url='/fund/login/')
def Registered(request):
  if request.membership_status==0:
    return redirect(NotMember)
  elif request.membership_status==1:
    return redirect(Projects)
  else:
    member = models.Member.objects.get(email=request.user.username)

  nship = request.GET.get('sh') or member.current #sh set by Projects, current set by Register
  try:
    ship = models.Membership.objects.get(pk=nship, member=member)
  except models.Membership.DoesNotExist: #only if they manually entered # or something went horribly wrong
    logging.warning('Membership does not exist right at /registered ' + request.user.username)
    return redirect(Home)
  if ship.approved==True: #another precaution
    logging.warning('Membership approved before check at /registered ' + request.user.username)
    return redirect(Home)
  
  proj = ship.giving_project
  if proj.pre_approved:
    app_list = [email.strip().lower() for email in proj.pre_approved.split(',')]
    logging.info('Checking pre-approval for ' + request.user.username + ' in ' + str(proj) + ', list: ' + proj.pre_approved)
    if ship.member.email in app_list:
      ship.approved = True
      ship.save()
      member.current = nship
      member.save()
      logging.info('Pre-approval succeeded')
      return redirect(Home)

  return render_to_response('fund/registered.html', {'member':member, 'proj':proj})

#MEMBERSHIP MANAGEMENT
@login_required(login_url='/fund/login/')
def Projects(request):
  logging.info('view')
  if request.membership_status==0:
    return redirect(NotMember)
  else:
    member = models.Member.objects.get(email=request.user.username)
  
  ships = member.membership_set.all()
  
  printout = ''
  if request.method=='POST':
    form = AddProjectForm(request.POST)
    if form.is_valid():
      gp = request.POST['giving_project']
      giv = models.GivingProject.objects.get(pk=gp)
      ship, new = models.Membership.objects.get_or_create(member = member, giving_project=giv)
      if new:
        return redirect('/fund/registered?sh='+str(ship.pk))
      else:
        printout = 'You are already registered with that giving project.'
  else:
    form = AddProjectForm()
  return render_to_response('fund/projects.html', {'member':member, 'form':form, 'printout':printout, 'ships':ships})

@login_required(login_url='/fund/login/')
@approved_membership()
def SetCurrent(request, ship_id):
  member = request.membership.member
  try:
    shippy = models.Membership.objects.get(pk=ship_id, member=member, approved=True)
  except models.Membership.DoesNotExist:
    return redirect(Projects)
  
  member.current=shippy.pk
  member.save()
  
  return redirect(Home)

# MAIN VIEWS
@login_required(login_url='/fund/login/')
@approved_membership()
def Home(request):
  
  #querydict for pre-loading forms
  logging.debug(request.GET.dict())
  step = request.GET.get('step')
  donor = request.GET.get('donor')
  type = request.GET.get('t')
  if step and donor and type:
    load = '/fund/'+donor+'/'+step
    if type=="complete":
      load += '/done'
    loadto = donor + '-nextstep'
  else:
    load = ''
    loadto = ''
  
  #member/ship info
  membership = request.membership
  member = membership.member
  
  #top content
  news = models.NewsItem.objects.filter(membership__giving_project=membership.giving_project).order_by('-date')
  header = membership.giving_project.title
  
  logging.debug(str(membership))
  
  #donors
  donors = list(membership.donor_set.all())
  progress = {'contacts':len(donors), 'estimated':0, 'talked':0, 'asked':0, 'pledged':0, 'donated':0} 
  donor_data = {}
  empty_date = datetime.date(2500,1,1)
  
  est = membership.giving_project.require_estimates()
  if load != '':
    est = False #override, don't check if following link from email
  else:
    amount_entered, amount_missing = False, False
    need_est, initiale = [], []
  
  for donor in donors:
    donor_data[donor.pk] = {'donor':donor, 'complete_steps':[], 'next_step':False, 'next_date':empty_date, 'overdue':False}
    progress['estimated'] += donor.estimated()
    if donor.asked:
      progress['asked'] += 1
      donor_data[donor.pk]['next_date'] = datetime.date(2600,1,1)
    elif donor.talked:
      progress['talked'] += 1
    if donor.pledged:
      progress['pledged'] += donor.pledged
      donor_data[donor.pk]['next_date'] = datetime.date(2700,1,1)
    if donor.gifted:
      progress['donated'] += donor.gifted
    if est:
      if donor.amount:
        amount_entered = True
      else:
        amount_missing = True
        initiale.append({'donor': donor})
        need_est.append(donor)
  
  #progress charts
  pie = {}
  if progress['contacts'] > 0:
    progress['bar'] = 100*progress['asked']/progress['contacts']
    progress['contactsremaining'] = progress['contacts'] - progress['talked'] -  progress['asked']
    progress['togo'] = progress['estimated'] - progress['pledged'] -  progress['donated']
    if progress['togo'] < 0:
      progress['togo'] = 0
  else:
    progress['contactsremaining'] = 0
  
  notif = membership.notifications
  if notif != '': #only show a notification once
    logging.info('Displaying notification: ' + notif)
    membership.notifications=''
    membership.save()

  #show estimates form
  if amount_missing:
    if amount_entered:
      #should not happen!
      logging.warning(str(membership) + ' has some contacts with estimates and some without.')
    EstFormset = formset_factory(DonorEstimates, extra=0)
    if request.method=='POST':
      formset = EstFormset(request.POST)
      logging.debug('Adding estimates - posted: ' + str(request.POST))
      if formset.is_valid():
        logging.debug('Adding estimates - is_valid passed, cycling through forms')
        for form in formset.cleaned_data:
          if form:
            current = form['donor']
            logging.debug(current)
            current.amount = form['amount']
            current.likelihood = form['likelihood']
            current.save()
            logging.debug('Amount & likelihood entered for ' + str(current))
        return HttpResponse("success")
    else:
      formset = EstFormset(initial=initiale)
      logging.info('Adding estimates - loading initial formset: ' +str(need_est))
    fd = zip(formset, need_est)
    
    #basic version for blocks
    step_list = list(models.Step.objects.filter(donor__membership=membership).order_by('date'))
    return render_to_response('fund/page_personal.html', 
      {'1active':'true',
      'header':header,
      'progress':progress,
      'member':member,
      'news':news,
      'steps':step_list,
      'membership':membership,
      'notif':notif,
      'formset':formset,
      'fd': fd,
      'load':load,
      'loadto':loadto,
      'pie':pie})
      
  #show regular contacts view
  else:  
   
    #steps
    step_list = list(models.Step.objects.filter(donor__membership=membership).order_by('date'))
    upcoming_steps = []
    ctz = timezone.get_current_timezone()
    today = ctz.normalize(timezone.now()).date()
    for step in step_list: #split into complete/not, attach to donors
      if step.completed:
        donor_data[step.donor_id]['complete_steps'].append(step)
      else:
        upcoming_steps.append(step)
        donor_data[step.donor_id]['next_step'] = step
        donor_data[step.donor_id]['next_date'] = step.date
        if step.date < today:
          donor_data[step.donor_id]['overdue'] = True
    upcoming_steps.sort(key = lambda step: step.date)
    donor_list = donor_data.values() #convert outer dict to list and sort it
    donor_list.sort(key = lambda donor: donor['next_date'])  
    
    suggested = membership.giving_project.suggested_steps.splitlines()
    suggested = filter(None, suggested) #move this to the admin save
  
    ContactFormset = formset_factory(MassDonor, extra=5)
    formset = ContactFormset()
    
    return render_to_response('fund/page_personal.html', 
    {'1active':'true',
    'header':header,
    'donor_list': donor_list,
    'progress':progress,
    'member':member,
    'news':news,
    'steps':upcoming_steps,
    'membership':membership,
    'notif':notif,
    'suggested':suggested,
    'formset':formset,
    'load':load,
    'loadto':loadto,
    'pie':pie})

@login_required(login_url='/fund/login/')
@approved_membership()
def ProjectPage(request):

  membership = request.membership
  member = membership.member
  project = membership.giving_project
  
  #blocks
  news = models.NewsItem.objects.filter(membership__giving_project=project).order_by('-date')
  steps = models.Step.objects.select_related('donor').filter(donor__membership=membership, completed__isnull=True).order_by('date')[:2]
  
  project_progress = {'contacts':0, 'talked':0, 'asked':0, 'pledged':0, 'donated':0}
  donors = list(models.Donor.objects.filter(membership__giving_project=project))
  project_progress['contacts'] = len(donors)
  for donor in donors:
    #project_progress['estimated'] += donor.estimated()
    if donor.asked:
      project_progress['asked'] += 1
    elif donor.talked:
      project_progress['talked'] += 1
    if donor.gifted:
      project_progress['donated'] += donor.gifted
    elif donor.pledged:
      project_progress['pledged'] += donor.pledged 
  
  project_progress['contactsremaining'] = project_progress['contacts'] - project_progress['talked'] -  project_progress['asked']
  project_progress['togo'] =  project.fund_goal - project_progress['pledged'] -  project_progress['donated']
  if project_progress['togo'] < 0:
    project_progress['togo'] = 0

  resources = models.ProjectResource.objects.filter(giving_project = project).select_related('resource')
  
  logging.info(resources)
  sectioned = {}
  for projresource in resources:
    session = str(projresource.session)
    if not session in sectioned:
       sectioned[session] = []
    sectioned[session].append(projresource.resource)
    
  #base
  header = project.title
 
  return render_to_response('fund/page_project.html', 
  {'2active':'true',
  'header':header,
  'news':news,
  'member':member,
  'steps':steps,
  'membership':membership,
  'project_progress':project_progress,
  'sectioned':sectioned})

@login_required(login_url='/fund/login/')
@approved_membership()
def ScoringList(request):
  
  membership = request.membership
  member = membership.member
  project = membership.giving_project
  
  #blocks
  news = models.NewsItem.objects.filter(membership__giving_project=project).order_by('-date')
  steps = models.Step.objects.filter(donor__membership=membership, completed__isnull=True).order_by('date')[:3]
  
  #base
  header = project.title
  
  grant_list = grants.models.GrantApplication.objects.all() #TEMP want to filter by gp
  logging.info("grant list:" + str(grant_list))
  
  unreviewed = []
  reviewed = []
  in_progress = []
  for grant in grant_list:
    try: 
      review = scoring.models.ApplicationRating.objects.get(application = grant, membership = membership)
      if review.submitted:
        reviewed.append(grant)
      else: 
        in_progress.append(grant)
    except scoring.models.ApplicationRating.DoesNotExist:
      unreviewed.append(grant)
  
  return render_to_response('fund/scoring_list.html',   {'3active':'true',   'header':header,   'news':news,   'member':member, 'steps':steps,   'membership':membership,   'grant_list':grant_list, 												   'unreviewed':unreviewed,   'reviewed':reviewed,   'in_progress':in_progress})

#ERROR & HELP PAGES
@login_required(login_url='/fund/login/')
def NotMember(request):
  member = request.user #not really member, just for sharing template code
  contact_url=settings.SUPPORT_FORM_URL
  return render_to_response('fund/not_member.html', {'member':member, 'contact_url':contact_url})

@login_required(login_url='/fund/login/')
def NotApproved(request):
  try:
    member = models.Member.objects.get(email=request.user.username)
  except models.Member.DoesNotExist:
    return redirect(NotMember)
  memberships = member.membership_set.all()
  return render_to_response('fund/not_approved.html', {'member':member, 'memberships':memberships})

def Blocked(request):
  contact_url = settings.SUPPORT_FORM_URL
  return render_to_response('fund/blocked.html', {'contact_url':contact_url})

def Support(request):
  header = "Support"
  if request.user:
    member = request.user #for shared template
  return render_to_response('fund/support.html', {'member':member, 'header':header})
  
#FORMS
#successful AJAX should return HttpResponse("success")

@login_required(login_url='/fund/login/')
@approved_membership()
def AddMult(request):
  est = request.membership.giving_project.require_estimates() #showing estimates t/f
  if est:
    ContactFormset = formset_factory(MassDonor, extra=5)
  else:
    ContactFormset = formset_factory(MassDonorPre, extra=5)
  if request.method=='POST':
    formset = ContactFormset(request.POST)
    if formset.is_valid():
      for form in formset.cleaned_data:
        if form:
          if est:
            contact = models.Donor(firstname = form['firstname'], lastname= form['lastname'], amount= form['amount'], likelihood= form['likelihood'], membership = request.membership)
          else:
            contact = models.Donor(firstname = form['firstname'], lastname= form['lastname'], membership = request.membership)
          contact.save()
      return HttpResponse("success")        
  else:
    formset = ContactFormset()

  if est:
    return render_to_response('fund/add_mult.html', {'formset':formset})
  else:
    return render_to_response('fund/add_mult_pre.html', {'formset':formset})

@login_required(login_url='/fund/login/')
@approved_membership()
def AddEstimates(request):
  initiald = [] #list of dicts for form initial
  dlist = [] #list of donors for zipping to formset
  membership = request.membership
  
  for donor in membership.donor_set.all():
    if not donor.amount:
      initiald.append({'donor': donor})
      dlist.append(donor)
  EstFormset = formset_factory(DonorEstimates, extra=0)
  if request.method=='POST':
    formset = EstFormset(request.POST)
    logging.debug('Adding estimates - posted: ' + str(request.POST))
    if formset.is_valid():
      logging.debug('Adding estimates - is_valid passed, cycling through forms')
      for form in formset.cleaned_data:
        if form:
          current = form['donor']
          logging.debug(current)
          current.amount = form['amount']
          current.likelihood = form['likelihood']
          current.save()
          logging.debug('Amount & likelihood entered for ' + str(current))
      return HttpResponse("success")
  else:
    formset = EstFormset(initial=initiald)
    logging.info('Adding estimates - loading initial formset, size ' + str(size) + ': ' +str(dlist))
  fd = zip(formset, dlist)
  return render_to_response('fund/add_estimates.html', {'formset':formset, 'fd':fd})

@login_required(login_url='/fund/login/')
@approved_membership()
def EditDonor(request, donor_id):

  try:
    donor = models.Donor.objects.get(pk=donor_id, membership=request.membership)
  except models.Donor.DoesNotExist:
    logging.error('Tried to edit a nonexist donor. User: ' + str(request.membership) + ', id given: '
     + str(donor_id))
    raise Http404
  
  est = request.membership.giving_project.require_estimates() #showing estimates t/f
  
  if request.method == 'POST':
    if est:
      form = models.DonorForm(request.POST, instance=donor, auto_id = str(donor.pk) + '_id_%s')
    else:
      form = models.DonorPreForm(request.POST, instance=donor, auto_id = str(donor.pk) + '_id_%s')
    if form.is_valid():
      form.save()
      request.membership.last_activity = timezone.now()
      request.membership.save()
      return HttpResponse("success")
  else:
    if est:
      form = models.DonorForm(instance=donor, auto_id = str(donor.pk) + '_id_%s')
    else:
      form = models.DonorPreForm(instance=donor, auto_id = str(donor.pk) + '_id_%s')
      
  return render_to_response('fund/edit_contact.html', { 'form': form, 'pk': donor.pk, 'action':'/fund/'+str(donor_id)+'/edit'})

@login_required(login_url='/fund/login/')
@approved_membership()
def DeleteDonor(request, donor_id):
  
  try:
    donor = models.Donor.objects.get(pk=donor_id, membership=request.membership)
  except models.Donor.DoesNotExist:
    return redirect(Home) #ADDERROR
    
  action = '/fund/'+str(donor_id)+'/delete'
  
  if request.method=='POST':
    request.membership.last_activity = timezone.now()
    request.membership.save()
    donor.delete()
    return redirect(Home)
    
  return render_to_response('fund/delete.html', {'action':action})

@login_required(login_url='/fund/login/')
@approved_membership()
def AddStep(request, donor_id):
  
  membership = request.membership
  suggested = membership.giving_project.suggested_steps.splitlines()
  
  logging.info('Single step - start of view.  User: ' + str(membership.member) + ', donor id: ' + str(donor_id))
  
  try:
    donor = models.Donor.objects.get(pk=donor_id, membership=membership)
  except models.Donor.DoesNotExist:
    logging.error('Single step - tried to add step to nonexistent donor.')
    return redirect(Home)
    
  action='/fund/'+donor_id+'/step'
  ajax = request.is_ajax()
  formid = 'addstep-'+donor_id
  divid = donor_id+'-addstep'
  
  if request.method == 'POST':
    form = models.StepForm(request.POST, auto_id = str(donor.pk) + '_id_%s')
    has_step = donor.next_step
    logging.info('Single step - POST: ' + str(request.POST))
    if has_step:
      logging.error('Donor already has an incomplete step: ' + str(has_step))
    elif form.is_valid():
      step = form.save(commit = False)
      step.donor = donor
      step.save()
      logging.info('Single step - form valid, step saved')
      donor.next_step = step
      donor.save()
      membership.last_activity = timezone.now()
      membership.save()
      return HttpResponse("success")
  else: 
    form = models.StepForm(auto_id = str(donor.pk) + '_id_%s')
    
  return render_to_response('fund/add_step.html', {'donor': donor, 'form': form, 'action':action, 'divid':divid, 'formid':formid, 'suggested':suggested, 'target': str(donor.pk) + '_id_description'})

@login_required(login_url='/fund/login/')
@approved_membership()
def AddMultStep(request):  
  initiald = [] #list of dicts for form initial
  dlist = [] #list of donors for zipping to formset
  size = 0
  membership = request.membership
  suggested = membership.giving_project.suggested_steps.splitlines()
  
  for donor in membership.donor_set.all():
    if not donor.next_step and not donor.pledged:
      initiald.append({'donor': donor})
      dlist.append(donor)
      size = size +1
  StepFormSet = formset_factory(MassStep, extra=0)
  if request.method=='POST':
    formset = StepFormSet(request.POST)
    logging.debug('Multiple steps - posted: ' + str(request.POST))
    if formset.is_valid():
      logging.debug('Multiple steps - is_valid passed, cycling through forms')
      for form in formset.cleaned_data:
        if form:
          step = models.Step(donor = form['donor'], date = form['date'], description = form['description'])
          step.save()
          step.donor.next_step = step
          step.donor.save()
          logging.info('Multiple steps - step created')
        else:
          logging.debug('Multiple steps - blank form')
      return HttpResponse("success")
  else:
    formset = StepFormSet(initial=initiald)
    logging.info('Multiple steps - loading initial formset, size ' + str(size) + ': ' +str(dlist))
  fd = zip(formset, dlist)
  return render_to_response('fund/add_mult_step.html', {'size':size, 'formset':formset, 'fd':fd, 'multi':True, 'suggested':suggested})

@login_required(login_url='/fund/login/')
@approved_membership()
def EditStep(request, donor_id, step_id):
  
  suggested = request.membership.giving_project.suggested_steps.splitlines()
  logging.info(suggested)
  
  try:
    donor = models.Donor.objects.get(pk=donor_id, membership=request.membership)
  except models.Donor.DoesNotExist:
    return redirect(Home) #ADDERROR
  
  try:
    step = models.Step.objects.get(id=step_id)
  except models.Step.DoesNotExist:
    return redirect(Home) #ADDERROR
    
  action='/fund/'+str(donor_id)+'/'+str(step_id)+'/'
  formid = 'editstep-'+donor_id
  divid = donor_id+'-nextstep'
  
  if request.method == 'POST':
      form = models.StepForm(request.POST, instance=step, auto_id = str(step.pk) + '_id_%s')
      if form.is_valid():
        request.membership.last_activity = timezone.now()
        request.membership.save()
        form.save()
        return HttpResponse("success")
  else:
    form = models.StepForm(instance=step, auto_id = str(step.pk) + '_id_%s')
    
  return render_to_response('fund/edit_step.html', { 'donor': donor, 'form': form, 'action':action, 'divid':divid, 'formid':formid, 'suggested':suggested, 'target': str(step.pk) + '_id_description'})

@login_required(login_url='/fund/login/')
@approved_membership()
def DoneStep(request, donor_id, step_id):
  
  membership = request.membership
  suggested = membership.giving_project.suggested_steps.splitlines()
  
  try:
    donor = models.Donor.objects.get(pk=donor_id, membership=membership)
  except models.Donor.DoesNotExist:
    return redirect(Home)
  
  try:
    step = models.Step.objects.get(id=step_id, donor=donor)
  except models.Step.DoesNotExist:
    return redirect(Home)
    
  action='/fund/'+str(donor_id)+'/'+str(step_id)+'/done'

  if request.method == 'POST':
    form = StepDoneForm(request.POST, auto_id = str(step.pk) + '_id_%s')
    if form.is_valid():
      membership.last_activity = timezone.now()
      membership.save()
      step.completed = timezone.now()
      donor.talked = True
      donor.notes = form.cleaned_data['notes']
      donor.next_step = None
      asked = form.cleaned_data['asked']
      response = form.cleaned_data['response']
      pledged = form.cleaned_data['pledged_amount']
      news = ' talked to a donor'
      if asked:
        if not donor.asked: #asked this step
          logging.debug('Asked this step')
          step.asked = True
          donor.asked = True
          news = ' asked a donor'
        if response=='3': #declined, doesn't matter whether new this step or not
          donor.pledged = 0
          logging.debug('Declined')
        if response=='2' and pledged and not donor.pledged: #pledged this step
          logging.debug('Pledge entered')
          step.pledged = pledged
          donor.pledged = pledged
      logging.info('Completing a step')
      step.save()
      #call story creator/updater
      deferred.defer(utils.UpdateStory, membership.pk, timezone.now())
      next = form.cleaned_data['next_step']
      next_date = form.cleaned_data['next_step_date']
      if next!='' and next_date!=None:
        form2 = models.StepForm().save(commit=False)
        form2.date = next_date
        form2.description = next
        form2.donor = donor
        ns = form2.save()
        logging.info(form2)
        donor.next_step = form2  
      donor.save()
      return HttpResponse("success")
  else: #GET - fill form with initial data
    response = 2
    amount = None
    if donor.pledged:
      if donor.pledged==0:
        response = 3
      else:
        response = 1
        amount = donor.pledged
    form = StepDoneForm(auto_id = str(step.pk) + '_id_%s', initial = {'asked':donor.asked, 'response':response, 'pledged_amount':amount, 'notes':donor.notes})
    
  return render_to_response('fund/done_step.html', {'form':form, 'action':action, 'donor':donor, 'suggested':suggested, 'target': str(step.pk) + '_id_next_step', 'step_id':step_id})

#CRON EMAILS
def EmailOverdue(request):
  #TODO - in email content, show all member overdue steps (not just for that ship)
  today = datetime.date.today()
  ships = models.Membership.objects.filter(giving_project__fundraising_deadline__gte=today)
  limit = today-datetime.timedelta(days=7)
  subject, from_email = 'Fundraising Steps', settings.APP_SEND_EMAIL
  for ship in ships:
    user = ship.member
    if ship.emailed <= limit:
      num, st = ship.has_overdue(next=True)
      if num>0 and st:
        logging.info(user.email + ' has overdue step(s), emailing.')
        to = user.email
        html_content = render_to_string('fund/email_overdue.html', {'login_url':settings.APP_BASE_URL+'fund/login', 'ship':ship, 'num':num, 'step':st, 'base_url':settings.APP_BASE_URL})
        text_content = strip_tags(html_content)
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to], ['sjfnwads@gmail.com'])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        ship.emailed = today
        ship.save()
  return HttpResponse("")

def NewAccounts(request):
  #Sends GP leaders an email saying how many unapproved memberships there are.  Will continue emailing about the same membership until it's approved/deleted.
  subject, from_email = 'Accounts pending approval', settings.APP_SEND_EMAIL
  for gp in models.GivingProject.objects.all():
    memberships = models.Membership.objects.filter(giving_project=gp, approved=False).count()
    leaders = models.Membership.objects.filter(giving_project=gp, leader=True)
    if memberships>0:
      for leader in leaders:
        to = leader.member.email
        html_content = render_to_string('fund/email_new_accounts.html', {'admin_url':settings.APP_BASE_URL+'admin/fund/membership/', 'count':memberships, 'support_email':settings.APP_SUPPORT_EMAIL})
        text_content = strip_tags(html_content)
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to], ['sjfnwads@gmail.com'])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
  return HttpResponse("")

def GiftNotify(request):
  #Sends an email to members letting them know gifts have been received
  #Marks donors as notified
  #Puts details in mem notif for main page
  donors = models.Donor.objects.filter(gifted__gt=0, gift_notified=False)
  members = []
  login_url = settings.APP_BASE_URL + 'fund/login'
  for donor in donors:
    members.append(donor.membership.member)
    donor.membership.notifications += 'Gift of $'+str(donor.gifted)+' received from '+donor.firstname+' '+donor.lastname+'!<br>'
    donor.membership.save()
  unique = set(members)
  subject, from_email = 'Gift received', settings.APP_SEND_EMAIL
  for mem in unique:
    to = mem.email
    html_content = render_to_string('fund/email_gift.html', {'login_url':login_url})
    text_content = strip_tags(html_content)
    msg = EmailMultiAlternatives(subject, text_content, from_email, [to], ['sjfnwads@gmail.com'])
    msg.attach_alternative(html_content, "text/html")
    msg.send()
  donors.update(gift_notified=True)
  return HttpResponse("")