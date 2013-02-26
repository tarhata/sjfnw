from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect, render_to_response
from sjfnw.fund.decorators import approved_membership
from sjfnw.grants.models import GrantApplication, GrantApplicationForm
import sjfnw.fund.models
import logging

# Scoring input

@login_required(login_url='/fund/login/')
@approved_membership()
def read_grant(request, app_id):
  membership = request.membership
  application = get_object_or_404(GrantApplication, pk = app_id)
  form = GrantApplicationForm()
  #potentially create them all ahead of time instead of this
  rating, new = models.ApplicationRating.objects.get_or_create(application = application, membership = membership)
  scoring_form = models.RatingForm(instance = rating)   
    
  return render_to_response("scoring/reading.html", {'scoring_form': scoring_form, 'app':application, 'form':form})

@login_required(login_url='/fund/login/')	
@approved_membership() 
def Save(request):
  if request.method=='POST':
    form = models.RatingForm(request.POST)
    if form.is_valid():
      logging.info('form is valid')
      if not request.is_ajax():
        logging.info('not ajax')
        form.submitted = True
        form.save()
        return redirect('/fund/apps')
      form.save()
      logging.info('INFO SAVED!')
    else:
      logging.info('form is not valid')
  return HttpResponse("")

#Viewing scores

@login_required(login_url='/fund/login/')
def specific_project_admin(request, project_id):
	
	project = get_object_or_404(GivingProject, pk = project_id)
	project_app_list = GrantApplication.objects.filter(grant_cycle = project.grant_cycle)
	total_ratings = models.ApplicationRating.objects.filter(membership__giving_project = project, submitted=True)
	dict = {}
	average_points = {}
	member_count = models.Membership.objects.filter(giving_project = project).count()
	
	for rating in total_ratings:
		if dict[rating.application]:
			dict[rating.application].append(rating)
		else:
			dict[rating.application]=[]
			dict[rating.application].append(rating)
    
	for application, reviews in dict:
		grand_total_points = 0
		for review in reviews:
			grand_total_points += review.total()
		average_points[application] = grand_total_points * 1.0 / len(application)
		average_points = sorted(average_points, key=lambda application: average_points[application], reverse=True)
	return render_to_response("scoring/project_summary.html", {"app_list":project_app_list, "dict":dict, "average_points":average_points })
	

	
@login_required(login_url='/fund/login/')
def all_giving_projects(request):	
	all_giving_projects = fund.models.GivingProject.objects.all()
	return render_to_response("scoring/single_giving_project.html", {"projects":all_giving_projects})
