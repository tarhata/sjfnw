from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.humanize.templatetags.humanize import intcomma
from django.core.mail import EmailMultiAlternatives
from django.core.urlresolvers import reverse
from django.forms.formsets import formset_factory
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from google.appengine.ext import deferred, ereporter

from sjfnw import constants
from sjfnw.grants.models import Organization, GrantApplication, ProjectApp

from sjfnw.fund.decorators import approved_membership
from sjfnw.fund import forms, modelforms, models, utils

import datetime, logging, os, json

if not settings.DEBUG:
  ereporter.register_logger()

logger = logging.getLogger('sjfnw')

# MAIN VIEWS

def get_block_content(membership, get_steps=True):
  """ Provide upper block content for the 3 main views

  Args:
    membership: current Membership
    get_steps: include list of upcoming steps or not (default True)

  Returns:
    steps: 2 closest upcoming steps
    news: news items, sorted by date descending
    grants: ProjectApps ordered by org name
  """

  bks = []
  # upcoming steps
  if get_steps:
    bks.append(models.Step.objects.select_related('donor')
                     .filter(donor__membership=membership,
                     completed__isnull=True).order_by('date')[:2])
  # project news
  bks.append(models.NewsItem.objects
            .filter(membership__giving_project=membership.giving_project)
            .order_by('-date')[:25])
  # grants
  p_apps = ProjectApp.objects.filter(giving_project=membership.giving_project)
  p_apps = p_apps.select_related('giving_project', 'application',
      'application__organization')
  # never show screened out by sub-committee
  p_apps = p_apps.exclude(pre_screening_status=45)
  if membership.giving_project.site_visits == 1:
    logger.info('Filtering grants for site visits')
    p_apps = p_apps.filter(screening_status__gte=70)
  p_apps = p_apps.order_by('application__organization__name')
  bks.append(p_apps)

  return bks

@login_required(login_url='/fund/login/')
@approved_membership()
def home(request):
  """ Handles display of the home/personal page

  Redirects:
    no contacts -> copy_contacts or add_mult
    contacts without estimates + post-training + no url params -> add_estimates

  Handles display of
    Top blocks
    Charts of personal progress
    List of donors, with details and associated steps
    Url param can trigger display of a form on a specific donor/step

  """

  membership = request.membership

  # check if there's a survey to fill out
  surveys = models.GPSurvey.objects.filter(
      giving_project=membership.giving_project, date__lte=timezone.now()
  ).exclude(
      id__in=json.loads(membership.completed_surveys)
  ).order_by('date')
  if surveys:
    logger.info('Needs to fill out survey; redirecting')
    return redirect(reverse('sjfnw.fund.views.gp_survey', kwargs = {'gp_survey': surveys[0].pk}))


  # check if they have contacts
  donors = membership.donor_set.all()
  if not donors:
    if not membership.copied_contacts:
      all_donors = models.Donor.objects.filter(membership__member=membership.member)
      logger.info(all_donors)
      if all_donors:
        return redirect(copy_contacts)
    return redirect(add_mult)

  #querydict for pre-loading forms
  step = request.GET.get('step')
  donor = request.GET.get('donor')
  form_type = request.GET.get('t')
  load_form = request.GET.get('load')
  if step and donor and form_type:
    load = '/fund/'+donor+'/'+step
    if form_type == "complete":
      load += '/done'
    loadto = donor + '-nextstep'
  elif load_form == 'stepmult':
    load = '/fund/stepmult'
    loadto = 'addmult'
  else:
    load = ''
    loadto = ''

    # check whether to redirect to add estimates
    if (membership.giving_project.require_estimates() and
        donors.filter(amount__isnull=True)):
      return redirect(add_estimates)

  # from here we know we're not redirecting

  #top content
  news, grants = get_block_content(membership, get_steps=False)
  header = membership.giving_project.title

  # collect & organize contact data
  prog = {'contacts':len(donors), 'estimated':0, 'talked':0, 'asked':0,
          'promised':0, 'received':0}
  donor_data = {}
  empty_date = datetime.date(2500, 1, 1)
  for donor in donors:
    donor_data[donor.pk] = {'donor':donor, 'complete_steps':[],
                            'next_step':False, 'next_date':empty_date,
                            'overdue':False}
    prog['estimated'] += donor.estimated()
    if donor.asked:
      prog['asked'] += 1
      donor_data[donor.pk]['next_date'] = datetime.date(2600, 1, 1)
    elif donor.talked:
      prog['talked'] += 1
    if donor.received() > 0:
      prog['received'] += donor.received()
      donor_data[donor.pk]['next_date'] = datetime.date(2800, 1, 1)
    elif donor.promised:
      prog['promised'] += donor.promised
      donor_data[donor.pk]['next_date'] = datetime.date(2700, 1, 1)

  # progress chart calculations
  if prog['contacts'] > 0:
    prog['bar'] = 100*prog['asked']/prog['contacts']
    prog['contactsremaining'] = (prog['contacts'] - prog['talked'] -
                                prog['asked'])
    prog['togo'] = (prog['estimated'] - prog['promised'] -
                    prog['received'])
    prog['header'] = '$' + intcomma(prog['estimated']) + ' fundraising goal'
    if prog['togo'] < 0:
      prog['togo'] = 0
      prog['header'] = ('$' + intcomma(prog['promised'] + prog['received']) +
                        ' raised')
  else:
    logger.error('No contacts but no redirect to add_mult')
    prog['contactsremaining'] = 0

  notif = membership.notifications #TODO replace with messages
  if notif and not settings.DEBUG: #on live, only show a notification once
    logger.info('Displaying notification to ' + str(membership) + ': ' + notif)
    membership.notifications = ''
    membership.save(skip=True)

  # get all steps
  step_list = list(models.Step.objects.filter(donor__membership=membership).order_by('date'))
  #split into complete/not, attach to donors
  upcoming_steps = []
  ctz = timezone.get_current_timezone()
  today = ctz.normalize(timezone.now()).date()
  for step in step_list:
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

  # suggested steps for step forms
  suggested = membership.giving_project.suggested_steps.splitlines()
  suggested = [sug for sug in suggested if sug] #filter out empty lines

  return render(request, 'fund/page_personal.html', {
    '1active':'true', 'header':header, 'news':news, 'grants':grants,
    'steps':upcoming_steps, 'donor_list': donor_list, 'progress':prog,
    'notif':notif, 'suggested':suggested, 'load':load, 'loadto':loadto})

@login_required(login_url='/fund/login/')
@approved_membership()
def project_page(request):

  membership = request.membership
  member = membership.member
  project = membership.giving_project

  #blocks
  steps, news, grants = get_block_content(membership)

  project_progress = {'contacts':0, 'talked':0, 'asked':0, 'promised':0, 'received':0}
  donors = list(models.Donor.objects.filter(membership__giving_project=project))
  project_progress['contacts'] = len(donors)
  for donor in donors:
    #project_progress['estimated'] += donor.estimated()
    if donor.asked:
      project_progress['asked'] += 1
    elif donor.talked:
      project_progress['talked'] += 1
    if donor.received() > 0:
      project_progress['received'] += donor.received()
    elif donor.promised:
      project_progress['promised'] += donor.promised

  project_progress['contactsremaining'] = project_progress['contacts'] - project_progress['talked'] -  project_progress['asked']
  project_progress['togo'] =  project.fund_goal - project_progress['promised'] -  project_progress['received']
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
  'steps':steps,
  'project_progress':project_progress,
  'resources':resources})

@login_required(login_url='/fund/login/')
@approved_membership()
def grant_list(request):

  membership = request.membership
  member = membership.member
  project = membership.giving_project

  #blocks
  steps, news, grants = get_block_content(membership)

  #base
  header = project.title

  return render(request, 'fund/grant_list.html',
      { '3active':'true', 'header':header, 'news':news,
        'steps':steps, 'membership':membership, 'grants':grants })

# LOGIN & REGISTRATION

def fund_login(request):
  error_msg = ''
  if request.method == 'POST':
    form = forms.LoginForm(request.POST)
    username = request.POST['email'].lower()
    password = request.POST['password']
    user = authenticate(username=username, password=password)
    if user:
      if user.is_active:
        login(request, user)
        return redirect(home)
      else:
        error_msg = 'Your account is not active.  Contact an administrator.'
        logger.warning("Inactive account tried to log in. Username: "+username)
    else:
      error_msg = "Your login and password didn't match."
  else:
    form = forms.LoginForm()
  logger.info(error_msg)
  return render(request, 'fund/login.html', {'form':form, 'error_msg':error_msg})

def fund_register(request):
  error_msg = ''
  if request.method == 'POST':
    register = forms.RegistrationForm(request.POST)
    if register.is_valid():
      username_email = request.POST['email'].lower()
      password = request.POST['password']
      #check Member already
      if models.Member.objects.filter(email = username_email):
        error_msg = 'That email is already registered.  <a href="/fund/login/">Login</a> instead.'
        logger.warning(username_email + ' tried to re-register')
      #check User already but not Member
      elif User.objects.filter(username=username_email):
        error_msg = 'That email is already registered through Social Justice Fund\'s online grant application.  Please use a different email address.'
        logger.warning('User already exists, but not Member: ' + username_email)
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
        logger.info('Registration - user and member objects created for ' + username_email)
        gp = request.POST['giving_project']
        if gp: #create Membership
          giv = models.GivingProject.objects.get(pk=gp)
          membership = models.Membership(member = member, giving_project = giv)
          membership.notifications = '<table><tr><td>Welcome to Project Central!<br>I\'m Odo, your Online Donor Organizing assistant. I\'ll be here to guide you through the fundraising process and cheer you on.</td><td><img src="/static/images/odo1.png" height=88 width=54 alt="Odo waving"></td></tr></table>'
          membership.save()
          member.current = membership.pk
          member.save()
          logger.info('Registration - membership in ' + str(giv) + 'created, welcome message set')
        #try to log in
        user = authenticate(username=username_email, password=password)
        if user:
          if user.is_active:
            login(request, user)
            return redirect('/fund/registered')
          else: #not active
            error_msg = 'Your account is not active. Please contact a site admin for assistance.'
            logger.error('Inactive right after registering. Email: ' + username_email)
        else: #email & pw didn't match
          error_msg = 'There was a problem with your registration.  Please <a href="/fund/support#contact">contact a site admin</a> for assistance.'
          logger.error("Password didn't match right after registering. Email: " + username_email)
  else: #GET
    register = forms.RegistrationForm()

  return render(request, 'fund/register.html', {'form':register, 'error_msg':error_msg})

@login_required(login_url='/fund/login/')
def registered(request):
  """ Sets up a member after registration TODO could this be a func instead of view?

  If they have no memberships, send them to projects page

  Checks membership for pre-approval status
  """

  if request.membership_status == 0:
    return redirect(not_member)
  elif request.membership_status == 1:
    return redirect(manage_account)
  else:
    member = models.Member.objects.get(email=request.user.username)

  nship = request.GET.get('sh') or member.current #sh set by manage_account, current set by Register
  try:
    ship = models.Membership.objects.get(pk=nship, member=member)
  except models.Membership.DoesNotExist: #only if they manually entered # or something went horribly wrong
    logger.warning('Membership does not exist right at /registered ' + request.user.username)
    return redirect(home)
  if ship.approved == True: #another precaution
    logger.warning('Membership approved before check at /registered ' + request.user.username)
    return redirect(home)

  proj = ship.giving_project
  if proj.pre_approved:
    app_list = [email.strip().lower() for email in proj.pre_approved.split(',')]
    logger.info('Checking pre-approval for ' + request.user.username + ' in ' + str(proj) + ', list: ' + proj.pre_approved)
    if ship.member.email in app_list:
      ship.approved = True
      ship.save(skip=True)
      member.current = nship
      member.save()
      logger.info('Pre-approval succeeded')
      return redirect(home)

  return render(request, 'fund/registered.html', {'member':member, 'proj':proj})

# MEMBERSHIP MANAGEMENT

@login_required(login_url='/fund/login/')
def manage_account(request):

  if request.membership_status == 0:
    return redirect(not_member)
  else:
    member = models.Member.objects.get(email=request.user.username)

  ships = member.membership_set.all()

  printout = ''
  if request.method == 'POST':
    form = forms.AddProjectForm(request.POST)
    if form.is_valid():
      logger.debug('Valid add project')
      gp = request.POST['giving_project']
      giv = models.GivingProject.objects.get(pk=gp)
      ship, new = models.Membership.objects.get_or_create(member = member, giving_project=giv)
      if new:
        return redirect('/fund/registered?sh='+str(ship.pk))
      else:
        printout = 'You are already registered with that giving project.'
  else:
    form = forms.AddProjectForm()
  return render(request, 'fund/projects.html', {'member':member, 'form':form, 'printout':printout, 'ships':ships})

@login_required(login_url='/fund/login/')
@approved_membership()
def set_current(request, ship_id):
  member = request.membership.member
  try:
    shippy = models.Membership.objects.get(pk=ship_id, member=member, approved=True)
  except models.Membership.DoesNotExist:
    return redirect(manage_account)

  member.current = shippy.pk
  member.save()

  return redirect(home)

# ERROR & HELP PAGES

@login_required(login_url='/fund/login/')
def not_member(request):
  try:
    org = Organization.objects.get(email=request.user.username)
  except Organization.DoesNotExist:
    org = False
  return render(request, 'fund/not_member.html', {'contact_url':'/fund/support#contact', 'org':org})

@login_required(login_url='/fund/login/')
def not_approved(request):
  try:
    member = models.Member.objects.get(email=request.user.username)
  except models.Member.DoesNotExist:
    return redirect(not_member)

  return render(request, 'fund/not_approved.html')

def blocked(request):
  return render(request, 'fund/blocked.html', {'contact_url':'/fund/support#contact'})

def support(request):
  member = False
  if request.membership_status > 1:
    member = request.membership.member
  elif request.membership_status == 1:
    member = models.Member.objects.get(email=request.user.username)
  return render(request, 'fund/support.html',
                {'member':member, 'support_email': constants.SUPPORT_EMAIL, 'support_form':constants.FUND_SUPPORT_FORM})


# ALTERNATIVE HOME PAGES


@login_required(login_url = '/fund/login')
@approved_membership()
def gp_survey(request, gp_survey):

  try:
    gp_survey = models.GPSurvey.objects.get(pk = gp_survey)
  except models.GPSurvey.DoesNotExist:
    logger.error('GP Survey does not exist ' + str(gp_survey))
    raise Http404('survey not found')


  if request.method == 'POST':
    logger.info(request.POST)
    form = modelforms.SurveyResponseForm(gp_survey.survey, request.POST)
    if form.is_valid():
      resp = form.save()
      logger.info('survey response saved')
      completed = json.loads(request.membership.completed_surveys)
      completed.append(gp_survey.pk)
      request.membership.completed_surveys = json.dumps(completed)
      request.membership.save()
      return HttpResponse('success')

  else: #GET
    form = modelforms.SurveyResponseForm(gp_survey.survey, initial={'gp_survey': gp_survey})

  steps, news, grants = get_block_content(request.membership)

  return render(request, 'fund/fill_gp_survey.html', {
    'form': form, 'survey': gp_survey.survey, 'news': news, 'steps': steps, 'grants': grants})



# CONTACTS

@login_required(login_url = '/fund/login')
@approved_membership()
def copy_contacts(request):

  # base formset
  copy_formset = formset_factory(forms.CopyContacts, extra=0)

  if request.method == 'POST':
    logger.info(request.POST)

    if 'skip' in request.POST:
      logger.info('User skipping copy contacts')
      request.membership.copied_contacts = True
      request.membership.save()
      return HttpResponse("success")

    else:
      formset = copy_formset(request.POST)
      logger.info('Copy contracts submitted')
      if formset.is_valid():
        for form in formset.cleaned_data:
          if form['select']:
            contact = models.Donor(membership = request.membership,
                firstname = form['firstname'], lastname = form['lastname'],
                phone = form['phone'], email = form['email'], notes = form['notes'])
            contact.save()
            logger.debug('Contact created')
        request.membership.copied_contacts = True
        request.membership.save()
        return HttpResponse("success")
      else: #invalid
        logger.warning('Copy formset somehow invalid?! ' + str(request.POST))
        logger.warning(formset.errors)

  else: #GET
    all_donors = models.Donor.objects.filter(membership__member=request.membership.member).order_by('firstname', 'lastname', '-added')
    # extract name, contact info, notes. handle duplicates
    initial_data = []
    for donor in all_donors:
      if (initial_data and donor.firstname == initial_data[-1]['firstname'] and
             (donor.lastname and donor.lastname == initial_data[-1]['lastname'] or
                 donor.phone and donor.phone == initial_data[-1]['phone'] or
                 donor.email and donor.email == initial_data[-1]['email'])): #duplicate - do not override
        logger.info('Duplicate found! ' + str(donor))
        initial_data[-1]['lastname'] = initial_data[-1]['lastname'] or donor.lastname
        initial_data[-1]['phone'] = initial_data[-1]['phone'] or donor.phone
        initial_data[-1]['email'] = initial_data[-1]['email'] or donor.email
        initial_data[-1]['notes'] += donor.notes
        initial_data[-1]['notes'] = initial_data[-1]['notes'][:253]
      else: #not duplicate; add a row
        initial_data.append({
            'firstname': donor.firstname, 'lastname': donor.lastname,
            'phone': donor.phone, 'email': donor.email, 'notes': donor.notes})

    logger.info('initial data list of ' + str(len(initial_data)))
    formset = copy_formset(initial=initial_data)
    logger.debug('Loading copy contacts formset')

  return render(request, 'fund/copy_contacts.html', {'formset': formset})


@login_required(login_url='/fund/login/')
@approved_membership()
def add_mult(request):
  """ Add multiple contacts
  GET is via redirect from home, and should render top blocks as well as form

  POST will be via AJAX and does not need block info
  (template extends only when not ajax)
  """

  membership = request.membership

  est = membership.giving_project.require_estimates() #showing estimates t/f
  if est:
    contact_formset = formset_factory(forms.MassDonor, extra=5)
  else:
    contact_formset = formset_factory(forms.MassDonorPre, extra=5)
  empty_error = ''

  if request.method == 'POST':
    membership.last_activity = timezone.now()
    membership.save()
    formset = contact_formset(request.POST)
    if formset.is_valid():
      if formset.has_changed():
        logger.info('AddMult valid formset')
        #count = 0
        donors = models.Donor.objects.filter(membership=membership)
        donors = [donor.firstname + ' ' + donor.lastname for donor in donors]
        duplicates = []
        for form in formset.cleaned_data:
          if form:
            confirm = form['confirm'] and form['confirm'] == '1'
            if not confirm and (form['firstname'] + ' ' + form['lastname'] in donors):
              initial = {'confirm': u'1',
                         'firstname': form['firstname'],
                         'lastname': form['lastname']}
              if est:
                initial['amount'] = form['amount']
                initial['likelihood'] = form['likelihood']
              duplicates.append(initial)

            else: # not a duplicate
              if est:
                contact = models.Donor(firstname = form['firstname'],
                                       lastname= form['lastname'],
                                       amount= form['amount'],
                                       likelihood= form['likelihood'],
                                       membership = membership)
              else:
                contact = models.Donor(firstname = form['firstname'],
                                       lastname= form['lastname'],
                                       membership = membership)
              contact.save()
              logger.info('contact created')
        if duplicates:
          logger.info('Showing confirmation page for duplicates: ' + str(duplicates))
          empty_error = '<ul class="errorlist"><li>The contacts below have the same name as contacts you have already entered. Press submit again to confirm that you want to add them.</li></ul>'
          if est:
            contact_formset = formset_factory(forms.MassDonor)
          else:
            contact_formset = formset_factory(forms.MassDonorPre)
          formset = contact_formset(initial=duplicates)
          return render(request, 'fund/add_mult_flex.html',
                  {'formset':formset, 'empty_error':empty_error})
        else:
          return HttpResponse("success")
      else: #empty formset
        empty_error = u'<ul class="errorlist"><li>Please enter at least one contact.</li></ul>'
    else: #invalid
      logger.info(formset.errors)
    return render(request, 'fund/add_mult_flex.html',
                  {'formset':formset, 'empty_error':empty_error})

  else: #GET
    formset = contact_formset()
    steps, news, grants = get_block_content(membership)
    header = membership.giving_project.title

    return render(request, 'fund/add_mult_flex.html', {
      '1active':'true', 'header':header, 'news': news, 'grants': grants,
      'steps': steps, 'formset': formset })



@login_required(login_url='/fund/login/')
@approved_membership()
def add_estimates(request):
  initiald = [] #list of dicts for form initial
  dlist = [] #list of donors for zipping to formset
  membership = request.membership

  # get all donors without estimates
  for donor in membership.donor_set.all():
    if not donor.amount:
      initiald.append({'donor': donor})
      dlist.append(donor)
  # create formset
  est_formset = formset_factory(forms.DonorEstimates, extra=0)

  if request.method == 'POST':
    membership.last_activity = timezone.now()
    membership.save(skip=True)
    formset = est_formset(request.POST)
    logger.debug('Adding estimates - posted: ' + str(request.POST))
    if formset.is_valid():
      logger.debug('Adding estimates - is_valid passed, cycling through forms')
      for form in formset.cleaned_data:
        if form:
          current = form['donor']
          current.amount = form['amount']
          current.likelihood = form['likelihood']
          current.save()
      return HttpResponse("success")
    else: #invalid form
      fd = zip(formset, dlist)
      return render(request, 'fund/add_estimates.html',
                {'formset':formset, 'fd':fd})
  else: #GET
    formset = est_formset(initial=initiald)
    logger.info('Adding estimates - loading initial formset, size ' +
                 str(len(dlist)))
    # get vars for base templates
    steps, news, grants = get_block_content(membership)

    fd = zip(formset, dlist)
    return render(request, 'fund/add_estimates.html',
        {'news': news, 'grants': grants, 'steps': steps,
         '1active': 'true', 'formset':formset, 'fd':fd})

@login_required(login_url='/fund/login/')
@approved_membership()
def edit_donor(request, donor_id):

  try:
    donor = models.Donor.objects.get(pk=donor_id, membership=request.membership)
  except models.Donor.DoesNotExist:
    logger.error('Tried to edit a nonexist donor. User: ' +
                  str(request.membership) + ', id given: ' + str(donor_id))
    raise Http404

  #check whether to require estimates
  est = request.membership.giving_project.require_estimates()

  if request.method == 'POST':
    logger.debug(request.POST)
    request.membership.last_activity = timezone.now()
    request.membership.save(skip=True)
    if est:
      form = modelforms.DonorForm(request.POST, instance=donor,
                              auto_id = str(donor.pk) + '_id_%s')
    else:
      form = modelforms.DonorPreForm(request.POST, instance=donor,
                                 auto_id = str(donor.pk) + '_id_%s')
    if form.is_valid():
      logger.info('Edit donor success')
      form.save()
      return HttpResponse("success")
  else:
    if est:
      form = modelforms.DonorForm(instance=donor, auto_id = str(donor.pk) +
                              '_id_%s')
    else:
      form = modelforms.DonorPreForm(instance=donor, auto_id = str(donor.pk) +
                                 '_id_%s')
  return render(request, 'fund/edit_contact.html',
                {'form': form, 'pk': donor.pk,
                 'action':'/fund/'+str(donor_id)+'/edit'})

@login_required(login_url='/fund/login/')
@approved_membership()
def delete_donor(request, donor_id):

  try:
    donor = models.Donor.objects.get(pk=donor_id, membership=request.membership)
  except models.Donor.DoesNotExist:
    logger.warning(str(request.user) + 'tried to delete nonexistent donor: ' +
                    str(donor_id))
    raise Http404

  action = '/fund/' + str(donor_id) + '/delete'

  if request.method == 'POST':
    request.membership.last_activity = timezone.now()
    request.membership.save(skip=True)
    donor.delete()
    return redirect(home)

  return render(request, 'fund/delete.html', {'action':action})

# STEPS

@login_required(login_url='/fund/login/')
@approved_membership()
def add_step(request, donor_id):

  membership = request.membership
  suggested = membership.giving_project.suggested_steps.splitlines()

  logger.info('Single step - start of view. ' + str(membership.member) +
               ', donor id: ' + str(donor_id))

  try:
    donor = models.Donor.objects.get(pk=donor_id, membership=membership)
  except models.Donor.DoesNotExist:
    logger.error('Single step - tried to add step to nonexistent donor.')
    raise Http404

  if donor.get_next_step():
    logger.error('Trying to add step, donor has an incomplete')
    raise Http404 #TODO better error

  action = '/fund/' + donor_id + '/step'
  formid = 'addstep-'+donor_id
  divid = donor_id+'-addstep'

  if request.method == 'POST':
    membership.last_activity = timezone.now()
    membership.save(skip=True)
    form = modelforms.StepForm(request.POST, auto_id = str(donor.pk) + '_id_%s')
    logger.info('Single step - POST: ' + str(request.POST))
    if form.is_valid():
      step = form.save(commit = False)
      step.donor = donor
      step.save()
      logger.info('Single step - form valid, step saved')
      return HttpResponse("success")
  else:
    form = modelforms.StepForm(auto_id = str(donor.pk) + '_id_%s')

  return render(request, 'fund/add_step.html',
                {'donor': donor, 'form': form, 'action':action, 'divid':divid,
                 'formid':formid, 'suggested':suggested,
                 'target': str(donor.pk) + '_id_description'})

@login_required(login_url='/fund/login/')
@approved_membership()
def add_mult_step(request):
  initiald = [] #list of dicts for form initial
  dlist = [] #list of donors for zipping to formset
  size = 0
  membership = request.membership
  suggested = membership.giving_project.suggested_steps.splitlines()

  for donor in membership.donor_set.order_by('-added'): #sort by added
    if (donor.received() == 0 and donor.promised is None and donor.get_next_step() is None):
      initiald.append({'donor': donor})
      dlist.append(donor)
      size = size +1
    if size > 9:
      break
  step_formset = formset_factory(forms.MassStep, extra=0)
  if request.method == 'POST':
    membership.last_activity = timezone.now()
    membership.save(skip=True)
    formset = step_formset(request.POST)
    logger.debug('Multiple steps - posted: ' + str(request.POST))
    if formset.is_valid():
      logger.debug('Multiple steps - is_valid passed, cycling through forms')
      for form in formset.cleaned_data:
        if form:
          step = models.Step(donor = form['donor'], date = form['date'],
                             description = form['description'])
          step.save()
          logger.info('Multiple steps - step created')
      return HttpResponse("success")
    else:
      logger.info('Multiple steps invalid')
  else:
    formset = step_formset(initial=initiald)
    logger.info('Multiple steps - loading initial formset, size ' + str(size) +
                 ': ' +str(dlist))
  fd = zip(formset, dlist)
  return render(request, 'fund/add_mult_step.html',
                {'size':size, 'formset':formset, 'fd':fd, 'multi':True,
                 'suggested':suggested})

@login_required(login_url='/fund/login/')
@approved_membership()
def edit_step(request, donor_id, step_id):

  suggested = request.membership.giving_project.suggested_steps.splitlines()
  logger.info(suggested)

  try:
    donor = models.Donor.objects.get(pk=donor_id,
                                     membership=request.membership)
  except models.Donor.DoesNotExist:
    logger.error(str(request.user) + 'edit step on nonexistent donor ' +
                  str(donor_id))
    raise Http404

  try:
    step = models.Step.objects.get(id=step_id)
  except models.Step.DoesNotExist:
    logger.error(str(request.user) + 'edit step on nonexistent step ' +
                  str(step_id))
    raise Http404

  action = '/fund/'+str(donor_id)+'/'+str(step_id)
  formid = 'editstep-'+donor_id
  divid = donor_id+'-nextstep'

  if request.method == 'POST':
    request.membership.last_activity = timezone.now()
    request.membership.save(skip=True)
    form = modelforms.StepForm(request.POST, instance=step, auto_id = str(step.pk) +
                           '_id_%s')
    if form.is_valid():
      logger.debug('Edit step success')
      form.save()
      return HttpResponse("success")
  else:
    form = modelforms.StepForm(instance=step, auto_id = str(step.pk) + '_id_%s')

  return render(request, 'fund/edit_step.html',
                {'donor': donor, 'form': form, 'action':action, 'divid':divid,
                'formid':formid, 'suggested':suggested,
                'target': str(step.pk) + '_id_description'})

@login_required(login_url='/fund/login/')
@approved_membership()
def done_step(request, donor_id, step_id):

  membership = request.membership
  suggested = membership.giving_project.suggested_steps.splitlines()

  try:
    donor = models.Donor.objects.get(pk=donor_id, membership=membership)
  except models.Donor.DoesNotExist:
    logger.error(str(request.user) + ' complete step on nonexistent donor ' +
                  str(donor_id))
    raise Http404

  try:
    step = models.Step.objects.get(id=step_id, donor=donor)
  except models.Step.DoesNotExist:
    logger.error(str(request.user) + ' complete step on nonexistent step ' +
                  str(step_id))
    raise Http404

  action = reverse('sjfnw.fund.views.done_step', kwargs={'donor_id': donor_id, 'step_id': step_id})

  if request.method == 'POST':
    # update membership activity timestamp
    membership.last_activity = timezone.now()
    membership.save(skip=True)

    # get posted form
    form = forms.StepDoneForm(request.POST, auto_id = str(step.pk) + '_id_%s')
    if form.is_valid():
      logger.info('Completing a step')

      step.completed = timezone.now()
      donor.talked = True
      donor.notes = form.cleaned_data['notes']

      asked = form.cleaned_data['asked']
      response = form.cleaned_data['response']
      promised = form.cleaned_data['promised_amount']

      # process ask-related input
      if asked:
        if not donor.asked: #asked this step
          logger.debug('Asked this step')
          step.asked = True
          donor.asked = True
        if response == '3': #declined, doesn't matter this step or not
          donor.promised = 0
          step.promised = 0
          logger.debug('Declined')
        if response == '1' and promised and not donor.promised: # pledged this step
          logger.debug('Promise entered')
          step.promised = promised
          donor.promised = promised
          donor.lastname = form.cleaned_data['last_name']
          donor.likely_to_join = form.cleaned_data['likely_to_join']
          logger.info(form.cleaned_data['likely_to_join'])
          donor.promise_reason = json.dumps(form.cleaned_data['promise_reason'])
          logger.info(form.cleaned_data['promise_reason'])
          phone = form.cleaned_data['phone']
          email = form.cleaned_data['email']
          if phone:
            donor.phone = phone
          if email:
            donor.email = email

      # save donor & completed step
      step.save()
      donor.save()

      #call story creator/updater
      if os.getenv('SERVER_SOFTWARE', '').startswith('Google App Engine'):
        deferred.defer(membership.update_story, timezone.now())
        logger.info('Calling update story')

      # process next step input
      next_step = form.cleaned_data['next_step']
      next_date = form.cleaned_data['next_step_date']
      if next_step != '' and next_date != None:
        form2 = modelforms.StepForm().save(commit=False)
        form2.date = next_date
        form2.description = next_step
        form2.donor = donor
        form2.save()
        logger.info('Next step created')

      return HttpResponse("success")
    else: #invalid form
      logger.info('Invalid step completion: ' + str(form.errors))

  else: #GET - fill form with initial data
    initial = {
        'asked': donor.asked, 'notes': donor.notes,'last_name': donor.lastname,
        'phone': donor.phone, 'email': donor.email,
        'promise_reason': json.loads(donor.promise_reason),
        'likely_to_join': donor.likely_to_join}
    if donor.promised:
      if donor.promised == 0:
        initial['response'] = 3
      else:
        initial['response'] = 1
        initial['promised_amount'] = donor.promised
    form = forms.StepDoneForm(auto_id = str(step.pk) + '_id_%s', initial = initial)

  return render(request, 'fund/done_step.html',
                {'form':form, 'action':action, 'donor':donor,
                 'suggested':suggested,
                 'target': str(step.pk) + '_id_next_step', 'step_id':step_id,
                 'step':step})

# CRON EMAILS
def email_overdue(request):
  #TODO - in email content, show all overdue steps (not just for that ship)
  today = datetime.date.today()
  ships = models.Membership.objects.filter(giving_project__fundraising_deadline__gte=today)
  limit = today-datetime.timedelta(days=7)
  subject, from_email = 'Fundraising Steps', constants.FUND_EMAIL
  for ship in ships:
    user = ship.member
    if not ship.emailed or (ship.emailed <= limit):
      num, st = ship.overdue_steps(get_next=True)
      if num > 0 and st:
        logger.info(user.email + ' has overdue step(s), emailing.')
        to = user.email
        html_content = render_to_string('fund/email_overdue.html',
                                        {'login_url':settings.APP_BASE_URL+'fund/login',
                                        'ship':ship, 'num':num, 'step':st,
                                        'base_url':settings.APP_BASE_URL})
        text_content = strip_tags(html_content)
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to],
                                     [constants.SUPPORT_EMAIL])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        ship.emailed = today
        ship.save(skip=True)
  return HttpResponse("")

def new_accounts(request):
  """
  Sends GP leaders an email saying how many unapproved memberships exist
  Will continue emailing about the same membership until it's approved/deleted.
  """
  subject, from_email = 'Accounts pending approval', constants.FUND_EMAIL
  for gp in models.GivingProject.objects.all():
    memberships = models.Membership.objects.filter(giving_project=gp, approved=False).count()
    leaders = models.Membership.objects.filter(giving_project=gp, leader=True)
    if memberships > 0:
      for leader in leaders:
        to = leader.member.email
        html_content = render_to_string('fund/email_new_accounts.html',
                                        {'admin_url':settings.APP_BASE_URL+'admin/fund/membership/',
                                        'count':memberships,
                                        'support_email':constants.SUPPORT_EMAIL})
        text_content = strip_tags(html_content)
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to],
                                     [constants.SUPPORT_EMAIL])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
  return HttpResponse("")

def gift_notify(request):
  """
  Send an email to members letting them know gifts have been received
  Mark donors as notified
  Put details in membership notif
  """

  donors = models.Donor.objects.filter(
      gift_notified=False
  ).exclude(
      received_this=0, received_next=0, received_afternext=0
  ).select_related('membership__member')
  memberships = {}
  for donor in donors: #group donors by membership
    if not donor.membership in memberships:
      memberships[donor.membership] = []
    memberships[donor.membership].append(donor)

  for ship, dlist in memberships.iteritems():
    gift_str = ''
    for d in dlist:
      gift_str += ('$' + str(d.received()) + ' gift or pledge received from ' +
                  d.firstname)
      if d.lastname:
        gift_str += ' '+d.lastname
      gift_str += '!<br>'
    ship.notifications = ('<table><tr><td>' + gift_str +
                         '</td><td><img src="/static/images/odo2.png"' +
                         'height=86 width=176 alt="Odo flying">' +
                         '</td></tr></table>')
    ship.save(skip=True)
    logger.info('Gift notification set for ' + str(ship))

  login_url = settings.APP_BASE_URL + 'fund/'
  subject, from_email = 'Gift or pledge received', constants.FUND_EMAIL
  for ship in memberships:
    to = ship.member.email
    html_content = render_to_string('fund/email_gift.html',
                                    {'login_url':login_url})
    text_content = strip_tags(html_content)
    msg = EmailMultiAlternatives(subject, text_content, from_email, [to],
                                 [constants.SUPPORT_EMAIL])
    msg.attach_alternative(html_content, "text/html")
    msg.send()
    logger.info('Emailed gift notification to ' + to)
  donors.update(gift_notified=True)
  return HttpResponse("")

def find_duplicates(request): #no url
  donors = (models.Donor.objects.select_related('membership')
                                .prefetch_related('step_set')
                                .order_by('firstname', 'lastname',
                                          'membership', '-talked'))
  ships = []
  deleted = 0
  prior = None
  for donor in donors:
    if (prior and donor.membership == prior.membership and
        donor.firstname == prior.firstname and donor.lastname and
        donor.lastname == prior.lastname and not donor.talked):
      #matches prev, no completed steps
      if donor.get_next_step():
        logger.warning('%s matched but has a step. Not deleting.' % unicode(donor))
        prior = donor
      else:
        logger.info('Deleting %s' % unicode(donor))
        donor.delete()
      deleted += 1
      if not donor.membership in ships:
        ships.append(donor.membership)
    else:
      prior = donor
  return render(request, 'fund/test.html', {'deleted':deleted, 'ships':ships})

