import logging
import models
from django.http import HttpResponse

def UpdateStory(membership_id, time):
  
  logging.info('UpdateStory running for membership ' + str(membership_id) + ' from ' + str(time))
  
  try: #get membership
    membership = models.Membership.objects.get(pk = membership_id)
  except models.Membership.DoesNotExist:
    logging.error('Update story - membership ' + str(membership_id) + ' does not exist')
    return HttpResponse("failure")
  
  #today's range
  today_min = time.replace(hour=0, minute=0, second=0)
  today_max = time.replace(hour=23, minute=59, second=59)
  
  #get or create newsitem object
  logging.debug('Checking for story with date between ' + str(today_min) + ' and ' + str(today_max))
  search = models.NewsItem.objects.filter(date__range=(today_min, today_max), membership=membership) 
  if search:
    story = search[0]
  else:
    story = models.NewsItem(date = time, membership=membership, summary = membership.member.first_name + 'news!!!')
  
  #tally today's steps
  steps = models.Step.objects.filter(completed__range=(today_min, today_max)).select_related('donor')
  logging.debug('Filtered steps: ' + str(steps))
  talked, asked, pledges, pledged = 0, 0, 0, 0
  donors = [] #for talk counts, don't want to double up
  for step in steps:
    if step.asked:
      asked += 1
      if step.donor in donors: #if they counted for talk from earlier step, remove
        talked -= 1
      else:
        donors.append(step.donor)
    elif not step.donor in donors:
      talked += 1
      donors.append(step.donor)
    if step.pledged:
      pledges += 1
      pledged += step.pledged
  summary = ''
  if pledged > 0:
    summary += ' and got $' + str(pledged) + ' in pledges'
    if asked>0:
      summary = ', asked ' + str(asked) + summary
  elif asked>0:
    summary += ' and asked ' + str(asked)
  talked_pluralize = ' contacts' if talked>1 else ' contact'
  summary = membership.member.first_name + ' talked to ' + str(talked) + talked_pluralize + summary
  summary += '.'
  logging.info(summary)
  story.summary = summary
  story.save()
  logging.info('Story saved')
  return HttpResponse("success")