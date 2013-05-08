from django import http, template, forms
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.humanize.templatetags.humanize import intcomma
from django.core.mail import EmailMultiAlternatives
from django.db import connection
from django.forms.formsets import formset_factory
from django.http import HttpResponse, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from decorators import approved_membership
from forms import *
from google.appengine.ext import deferred, ereporter
from sjfnw import constants
from sjfnw.grants.models import Organization, GrantApplication
import pytz, utils, json, models, datetime, random, logging

if not settings.DEBUG:
  ereporter.register_logger()

# MAIN VIEWS

def get_block_content(membership, first=True):
  contents = []
  if first: #home page does its own thing
     contents.append(models.Step.objects.select_related('donor').filter(donor__membership=membership, completed__isnull=True).order_by('date')[:2])
  contents.append(models.NewsItem.objects.filter(membership__giving_project=membership.giving_project).order_by('-date'))
  contents.append(GrantApplication.objects.filter(giving_project=membership.giving_project, screening_status__gte=50))
  logging.info(contents)
  return contents

@login_required(login_url='/fund/login/')
@approved_membership()
def Home(request):
  #hacks
  mult_template = 'fund/add_mult.html'
  formset = ''
  
  #querydict for pre-loading forms
  step = request.GET.get('step')
  donor = request.GET.get('donor')
  type = request.GET.get('t')
  load_form = request.GET.get('load')
  if step and donor and type:
    load = '/fund/'+donor+'/'+step
    if type=="complete":
      load += '/done'
    loadto = donor + '-nextstep'
  elif load_form == 'stepmult':
    load = '/fund/stepmult'
    loadto = 'addmult'
  else:  
    load = ''
    loadto = ''
  
  #member/ship info
  membership = request.membership
  member = membership.member
  
  #top content
  news, grants = get_block_content(membership, first=False)
  logging.info(news)
  logging.info(grants)
  header = membership.giving_project.title

  #donors
  donors = list(membership.donor_set.all())
  progress = {'contacts':len(donors), 'estimated':0, 'talked':0, 'asked':0, 'pledged':0, 'donated':0} 
  donor_data = {}
  empty_date = datetime.date(2500,1,1)
  
  #checking for direct links from emails & whether ests are req
  est = membership.giving_project.require_estimates()
  add_est = est
  if load != '':
    add_est = False #override, don't check if following link from email
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
    if donor.gifted:
      progress['donated'] += donor.gifted
      donor_data[donor.pk]['next_date'] = datetime.date(2800,1,1)
    elif donor.pledged:
      progress['pledged'] += donor.pledged
      donor_data[donor.pk]['next_date'] = datetime.date(2700,1,1)
    if add_est:
      if donor.amount is not None:
        amount_entered = True
      else:
        amount_missing = True
        initiale.append({'donor': donor})
        need_est.append(donor)
  
  #progress charts
  if progress['contacts'] > 0:
    progress['bar'] = 100*progress['asked']/progress['contacts']
    progress['contactsremaining'] = progress['contacts'] - progress['talked'] -  progress['asked']
    progress['togo'] = progress['estimated'] - progress['pledged'] -  progress['donated']
    progress['header'] = '$%s fundraising goal' % intcomma(progress['estimated'])
    if progress['togo'] < 0:
      progress['togo'] = 0
      progress['header'] = '$%s raised' % intcomma(progress['pledged'] + progress['donated'])
  else:
    progress['contactsremaining'] = 0
  
  notif = membership.notifications
  if notif and not settings.DEBUG: #on live, only show a notification once
    logging.info('Displaying notification to ' + str(membership) + ': ' + notif)
    membership.notifications=''
    membership.save(skip=True)

  #show estimates form
  if add_est and amount_missing:
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
    return render(request, 'fund/page_personal.html', 
      {'1active':'true',
      'header':header,
      'progress':progress,
      'member':member,
      'news':news,
      'grants':grants,
      'steps':step_list,
      'membership':membership,
      'notif':notif,
      'formset':formset,
      'fd': fd,
      'load':load,
      'loadto':loadto})
      
  #show regular contacts view
  else:  
    if donors:
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
      
    else: #no donors - showing mass form
      donor_list, upcoming_steps = [], [] #FIX
      if est:
        ContactFormset = formset_factory(MassDonor, extra=5)
        mult_template = 'fund/add_mult.html'
      else:
        ContactFormset = formset_factory(MassDonorPre, extra=5)
        mult_template = 'fund/add_mult_pre.html'
      formset = ContactFormset()
    
    suggested = membership.giving_project.suggested_steps.splitlines()
    suggested = filter(None, suggested) #move this to the admin save    
    
    return render(request, 'fund/page_personal.html', {
      '1active':'true',
      'header':header,
      'donor_list': donor_list,
      'progress':progress,
      'member':member,
      'news':news,
      'grants':grants,
      'steps':upcoming_steps,
      'membership':membership,
      'notif':notif,
      'suggested':suggested,
      'formset':formset,
      'load':load,
      'loadto':loadto,
      'mult_template':mult_template})

@login_required(login_url='/fund/login/')
@approved_membership()
def ProjectPage(request):

  membership = request.membership
  member = membership.member
  project = membership.giving_project
  
  #blocks
  steps, news, grants = get_block_content(membership)
  
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

  resources = models.ProjectResource.objects.filter(giving_project = project).select_related('resource').order_by('session')
    
  #base
  header = project.title
 
  return render(request, 'fund/page_project.html', 
  {'2active':'true',
  'header':header,
  'news':news,
  'grants':grants,
  'member':member,
  'steps':steps,
  'membership':membership,
  'project_progress':project_progress,
  'resources':resources})

@login_required(login_url='/fund/login/')
@approved_membership()
def GrantList(request):
  
  membership = request.membership
  member = membership.member
  project = membership.giving_project
  
  #blocks
  steps, news, grants = get_block_content(membership)
  
  #base
  header = project.title
  
  return render(request, 'fund/grant_list.html',
    { '3active':'true',
      'header':header,
      'news':news,
      'member':member,
      'steps':steps,
      'membership':membership,
      'grants':grants,
    })

# LOGIN & REGISTRATION
def FundLogin(request):
  error_msg=''
  if request.method=='POST':
    form = LoginForm(request.POST)
    username = request.POST['email'].lower()
    password = request.POST['password']
    user = authenticate(username=username, password=password)
    if user:
      if user.is_active:
        login(request, user)
        return redirect(Home)
      else:
        error_msg='Your account is not active.  Contact an administrator.'
        logging.warning("Inactive account tried to log in. Username: "+username)
    else:
      error_msg ="Your login and password didn't match."
  else:
    form = LoginForm()
  return render(request, 'fund/login.html', {'form':form, 'error_msg':error_msg})

def Register(request):
  error_msg = ''
  if request.method=='POST':
    register = RegistrationForm(request.POST)
    if register.is_valid():
      username_email = request.POST['email'].lower()
      password = request.POST['password']     
      #check Member already
      if models.Member.objects.filter(email = username_email):
        error_msg = 'That email is already registered.  <a href="/fund/login/">Login</a> instead.'
        logging.info(username_email + ' tried to re-register')
      #check User already but not Member
      elif User.objects.filter(username=username_email):
        error_msg = 'That email is already registered through Social Justice Fund\'s online grant application.  Please use a different email address.'
        logging.warning('User already exists, but not Member: ' + username_email)
      #clear to register
      else:
        #create User and Member
        new_user = User.objects.create_user(username_email, username_email, password)
        fn = request.POST['first_name']
        ln = request.POST['last_name']
        new_user.first_name = fn
        new_user.last_name = ln
        new_user.save()
        member = models.Member(email = username_email, first_name = fn, last_name = ln)
        member.save()
        logging.info('Registration - user and member objects created for ' + username_email)
        gp = request.POST['giving_project']
        if gp: #create Membership
          giv = models.GivingProject.objects.get(pk=gp)
          membership = models.Membership(member = member, giving_project = giv)
          membership.notifications = '<table><tr><td>Welcome to Project Central!<br>I\'m Odo, your Online Donor Organizing assistant. I\'ll be here to guide you through the fundraising process and cheer you on.</td><td><img src="/static/images/odo1.png" height=88 width=54 alt="Odo waving"></td></tr></table>'
          membership.save()
          member.current = membership.pk
          member.save()
          logging.info('Registration - membership in ' + str(giv) + 'created, welcome message set')
        #try to log in
        user = authenticate(username=username_email, password=password)
        if user:
          if user.is_active:
            login(request, user)
            return redirect('/fund/registered')
          else: #not active
            error_msg = 'Your account is not active. Please contact a site admin for assistance.'
            logging.error('Inactive right after registering. Email: ' + username_email)
        else: #email & pw didn't match
          error_msg = 'There was a problem with your registration.  Please <a href="/fund/support#contact">contact a site admin</a> for assistance.'
          logging.error("Password didn't match right after registering. Email: " + username_email)
  else: #GET
    register = RegistrationForm()
    
  return render(request, 'fund/register.html', {'form':register, 'error_msg':error_msg})

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
      ship.save(skip=True)
      member.current = nship
      member.save()
      logging.info('Pre-approval succeeded')
      return redirect(Home)

  return render(request, 'fund/registered.html', {'member':member, 'proj':proj})

#MEMBERSHIP MANAGEMENT
@login_required(login_url='/fund/login/')
def Projects(request):

  if request.membership_status==0:
    return redirect(NotMember)
  else:
    member = models.Member.objects.get(email=request.user.username)
  
  ships = member.membership_set.all()
  
  printout = ''
  if request.method=='POST':
    form = AddProjectForm(request.POST)
    if form.is_valid():
      logging.debug('Valid add project')
      gp = request.POST['giving_project']
      giv = models.GivingProject.objects.get(pk=gp)
      ship, new = models.Membership.objects.get_or_create(member = member, giving_project=giv)
      if new:
        return redirect('/fund/registered?sh='+str(ship.pk))
      else:
        printout = 'You are already registered with that giving project.'
  else:
    form = AddProjectForm()
  return render(request, 'fund/projects.html', {'member':member, 'form':form, 'printout':printout, 'ships':ships})

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

#ERROR & HELP PAGES
@login_required(login_url='/fund/login/')
def NotMember(request):
  try:
    org = Organization.objects.get(email=request.user.username)
  except Organization.DoesNotExist:
    org = False
  return render(request, 'fund/not_member.html', {'contact_url':'/fund/support#contact', 'org':org})

@login_required(login_url='/fund/login/')
def NotApproved(request):
  try:
    member = models.Member.objects.get(email=request.user.username)
  except models.Member.DoesNotExist:
    return redirect(NotMember)
  memberships = member.membership_set.all()
  return render(request, 'fund/not_approved.html')

def Blocked(request):
  return render(request, 'fund/blocked.html', {'contact_url':'/fund/support#contact'})

def Support(request):
  member = False
  if request.membership_status>1:
    member = request.membership.member
  elif request.membership_status==1:
    member = models.Member.objects.get(email=request.user.username)
  return render(request, 'fund/support.html', {'member':member, 'support_email': constants.SUPPORT_EMAIL, 'support_form':constants.FUND_SUPPORT_FORM})
  
#FORMS
@login_required(login_url='/fund/login/')
@approved_membership()
def AddMult(request):
  logging.info(request.path)
  membership = request.membership
  est = membership.giving_project.require_estimates() #showing estimates t/f
  if est:
    ContactFormset = formset_factory(MassDonor, extra=5)
  else:
    ContactFormset = formset_factory(MassDonorPre, extra=5)
  empty_error = ''
  if request.method=='POST':
    membership.last_activity = timezone.now()
    membership.save()
    logging.info(request.POST)
    formset = ContactFormset(request.POST)
    if formset.is_valid():
      if formset.has_changed():
        logging.info('AddMult valid formset')
        count = 0
        for form in formset.cleaned_data:
          if form:
            count += 1
            if est:
              contact = models.Donor(firstname = form['firstname'], lastname= form['lastname'], amount= form['amount'], likelihood= form['likelihood'], membership = membership)
            else:
              contact = models.Donor(firstname = form['firstname'], lastname= form['lastname'], membership = membership)
            contact.save()
        return HttpResponse("success")
      else: #empty formset
        empty_error = u'<ul class="errorlist"><li>Please enter at least one contact.</li></ul>'
    else: #invalid
      logging.info(formset.errors)
  else:
    formset = ContactFormset()

  if est:
    return render(request, 'fund/add_mult.html', {'formset':formset, 'empty_error':empty_error})
  else:
    return render(request, 'fund/add_mult_pre.html', {'formset':formset, 'empty_error':empty_error})

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
    membership.last_activity = timezone.now()
    membership.save(skip=True)
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
  return render(request, 'fund/add_estimates.html', {'formset':formset, 'fd':fd})

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
    logging.info(request.body)
    logging.info(request.POST)
    request.membership.last_activity = timezone.now()
    request.membership.save(skip=True)
    if est:
      form = models.DonorForm(request.POST, instance=donor, auto_id = str(donor.pk) + '_id_%s')
    else:
      form = models.DonorPreForm(request.POST, instance=donor, auto_id = str(donor.pk) + '_id_%s')
    if form.is_valid():
      logging.info('Edit donor success')
      form.save()
      return HttpResponse("success")
  else:
    if est:
      form = models.DonorForm(instance=donor, auto_id = str(donor.pk) + '_id_%s')
    else:
      form = models.DonorPreForm(instance=donor, auto_id = str(donor.pk) + '_id_%s')  
  return render(request, 'fund/edit_contact.html', { 'form': form, 'pk': donor.pk, 'action':'/fund/'+str(donor_id)+'/edit'})

@login_required(login_url='/fund/login/')
@approved_membership()
def DeleteDonor(request, donor_id):
  
  try:
    donor = models.Donor.objects.get(pk=donor_id, membership=request.membership)
  except models.Donor.DoesNotExist:
    logging.warning(str(request.user) + 'tried to delete nonexistant donor: ' + str(donor_id))
    raise Http404
    
  action = '/fund/'+str(donor_id)+'/delete'
  
  if request.method=='POST':
    request.membership.last_activity = timezone.now()
    request.membership.save(skip=True)
    donor.delete()
    return redirect(Home)
    
  return render(request, 'fund/delete.html', {'action':action})

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
    raise Http404
    
  action='/fund/'+donor_id+'/step'
  ajax = request.is_ajax()
  formid = 'addstep-'+donor_id
  divid = donor_id+'-addstep'
  
  if request.method == 'POST':
    membership.last_activity = timezone.now()
    membership.save(skip=True)
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
      return HttpResponse("success")
  else: 
    form = models.StepForm(auto_id = str(donor.pk) + '_id_%s')
    
  return render(request, 'fund/add_step.html', {'donor': donor, 'form': form, 'action':action, 'divid':divid, 'formid':formid, 'suggested':suggested, 'target': str(donor.pk) + '_id_description'})

@login_required(login_url='/fund/login/')
@approved_membership()
def AddMultStep(request):  
  initiald = [] #list of dicts for form initial
  dlist = [] #list of donors for zipping to formset
  size = 0
  membership = request.membership
  suggested = membership.giving_project.suggested_steps.splitlines()
  
  for donor in membership.donor_set.order_by('-added'): #sort by added
    if not (donor.next_step or (donor.pledged is not None) or donor.gifted):
      initiald.append({'donor': donor})
      dlist.append(donor)
      size = size +1
    if size > 9:
      break
  StepFormSet = formset_factory(MassStep, extra=0)
  if request.method=='POST':
    membership.last_activity = timezone.now()
    membership.save(skip=True)
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
      return HttpResponse("success")
    else:
      logging.info('Multiple steps invalid')
  else:
    formset = StepFormSet(initial=initiald)
    logging.info('Multiple steps - loading initial formset, size ' + str(size) + ': ' +str(dlist))
  fd = zip(formset, dlist)
  return render(request, 'fund/add_mult_step.html', {'size':size, 'formset':formset, 'fd':fd, 'multi':True, 'suggested':suggested})

@login_required(login_url='/fund/login/')
@approved_membership()
def EditStep(request, donor_id, step_id):
  
  suggested = request.membership.giving_project.suggested_steps.splitlines()
  logging.info(suggested)
  
  try:
    donor = models.Donor.objects.get(pk=donor_id, membership=request.membership)
  except models.Donor.DoesNotExist:
    logging.error(str(request.user) + 'edit step on nonexistent donor ' + str(donor_id))
    raise Http404
  
  try:
    step = models.Step.objects.get(id=step_id)
  except models.Step.DoesNotExist:
    logging.error(str(request.user) + 'edit step on nonexistent step ' + str(step_id))
    raise Http404
    
  action='/fund/'+str(donor_id)+'/'+str(step_id)
  formid = 'editstep-'+donor_id
  divid = donor_id+'-nextstep'
  
  if request.method == 'POST':
    request.membership.last_activity = timezone.now()
    request.membership.save(skip=True)
    form = models.StepForm(request.POST, instance=step, auto_id = str(step.pk) + '_id_%s')
    if form.is_valid():
      logging.debug('Edit step success')
      form.save()
      return HttpResponse("success")
  else:
    form = models.StepForm(instance=step, auto_id = str(step.pk) + '_id_%s')
    
  return render(request, 'fund/edit_step.html', { 'donor': donor, 'form': form, 'action':action, 'divid':divid, 'formid':formid, 'suggested':suggested, 'target': str(step.pk) + '_id_description'})

@login_required(login_url='/fund/login/')
@approved_membership()
def DoneStep(request, donor_id, step_id):
  
  membership = request.membership
  suggested = membership.giving_project.suggested_steps.splitlines()
  
  try:
    donor = models.Donor.objects.get(pk=donor_id, membership=membership)
  except models.Donor.DoesNotExist:
    logging.error(str(request.user) + ' complete step on nonexistent donor ' + str(donor_id))
    raise Http404
  
  try:
    step = models.Step.objects.get(id=step_id, donor=donor)
  except models.Step.DoesNotExist:
    logging.error(str(request.user) + ' complete step on nonexistent step ' + str(step_id))
    raise Http404
    
  action='/fund/'+str(donor_id)+'/'+str(step_id)+'/done'

  if request.method == 'POST':
    membership.last_activity = timezone.now()
    membership.save(skip=True)
    form = StepDoneForm(request.POST, auto_id = str(step.pk) + '_id_%s')
    if form.is_valid():
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
          step.pledged = 0
          logging.debug('Declined')
        if response=='1' and pledged and not donor.pledged: #pledged this step
          logging.debug('Pledge entered')
          step.pledged = pledged
          donor.pledged = pledged
          donor.lastname = form.cleaned_data['last_name']
          phone = form.cleaned_data['phone']
          email = form.cleaned_data['email']
          if phone:
            donor.phone = phone
          if email:
            donor.email = email
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
        donor.next_step = ns  
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
    form = StepDoneForm(auto_id = str(step.pk) + '_id_%s', initial = {'asked':donor.asked, 'response':response, 'pledged_amount':amount, 'notes':donor.notes, 'last_name':donor.lastname, 'phone':donor.phone, 'email':donor.email})
    
  return render(request, 'fund/done_step.html', {'form':form, 'action':action, 'donor':donor, 'suggested':suggested, 'target': str(step.pk) + '_id_next_step', 'step_id':step_id, 'step':step})

#CRON EMAILS
def EmailOverdue(request):
  #TODO - in email content, show all member overdue steps (not just for that ship)
  today = datetime.date.today()
  ships = models.Membership.objects.filter(giving_project__fundraising_deadline__gte=today)
  limit = today-datetime.timedelta(days=7)
  subject, from_email = 'Fundraising Steps', constants.FUND_EMAIL
  for ship in ships:
    user = ship.member
    if not ship.emailed or (ship.emailed <= limit):
      num, st = ship.has_overdue(next=True)
      if num>0 and st:
        logging.info(user.email + ' has overdue step(s), emailing.')
        to = user.email
        html_content = render_to_string('fund/email_overdue.html', {'login_url':settings.APP_BASE_URL+'fund/login', 'ship':ship, 'num':num, 'step':st, 'base_url':settings.APP_BASE_URL})
        text_content = strip_tags(html_content)
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to], [constants.SUPPORT_EMAIL])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        ship.emailed = today
        ship.save(skip=True)
  return HttpResponse("")

def NewAccounts(request):
  #Sends GP leaders an email saying how many unapproved memberships there are.  Will continue emailing about the same membership until it's approved/deleted.
  subject, from_email = 'Accounts pending approval', constants.FUND_EMAIL
  for gp in models.GivingProject.objects.all():
    memberships = models.Membership.objects.filter(giving_project=gp, approved=False).count()
    leaders = models.Membership.objects.filter(giving_project=gp, leader=True)
    if memberships>0:
      for leader in leaders:
        to = leader.member.email
        html_content = render_to_string('fund/email_new_accounts.html', {'admin_url':settings.APP_BASE_URL+'admin/fund/membership/', 'count':memberships, 'support_email':constants.SUPPORT_EMAIL})
        text_content = strip_tags(html_content)
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to], [constants.SUPPORT_EMAIL])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
  return HttpResponse("")

def GiftNotify(request):
  """ Send an email to members letting them know gifts have been received
    Mark donors as notified
    Put details in membership notif """

  donors = models.Donor.objects.filter(gifted__gt=0, gift_notified=False).select_related('membership__member')
  memberships = {}
  for donor in donors: #group donors by membership
    if not donor.membership in memberships:
      memberships[donor.membership] = []
    memberships[donor.membership].append(donor)
  
  for ship, dlist in memberships.iteritems():
    gift_str = ''
    for d in dlist:
      gift_str += 'Gift of $'+str(d.gifted)+' received from '+d.firstname
      if d.lastname:
        gift_str += ' '+d.lastname
      gift_str += '!<br>'
    ship.notifications = '<table><tr><td>' + gift_str + '</td><td><img src="/static/images/odo2.png" height=86 width=176 alt="Odo flying"></td></tr></table>'
    ship.save(skip=True)
    logging.info('Gift notification set for ' + str(ship))
  
  login_url = settings.APP_BASE_URL + 'fund/'
  subject, from_email = 'Gift received', constants.FUND_EMAIL
  for ship in memberships:
    to = ship.member.email
    html_content = render_to_string('fund/email_gift.html', {'login_url':login_url})
    text_content = strip_tags(html_content)
    msg = EmailMultiAlternatives(subject, text_content, from_email, [to], [constants.SUPPORT_EMAIL])
    msg.attach_alternative(html_content, "text/html")
    msg.send()
    logging.info('Emailed gift notification to ' + to)
  donors.update(gift_notified=True)
  return HttpResponse("")
  
def FindDuplicates(request): #no url
  donors = models.Donor.objects.select_related('membership').order_by('firstname', 'lastname', 'membership', '-next_step')
  ships = []
  deleted = 0
  prior = None
  matching = False
  for donor in donors:
    if prior and donor.membership == prior.membership and donor.firstname == prior.firstname and donor.lastname and donor.lastname == prior.lastname and not donor.talked: #matches prev, no completed steps
      matching = True
      donor.delete()
      deleted += 1
      if not donor.membership in ships:
        ships.append(donor.membership)
    else:
      if matching: #break, reset
        matching = False
      prior = donor
  return render(request, 'fund/test.html', {'deleted':deleted, 'ships':ships})