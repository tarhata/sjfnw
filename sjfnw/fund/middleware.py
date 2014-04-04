from sjfnw.fund import models
import logging
logger = logging.getLogger('sjfnw')

#sets request.membership, request.membership_status
class MembershipMiddleware(object):

  #checks
  # member exists
  # membership exists (try to find one that does)
  # membership is approved (try to find one that is)

  #changes to member.current
  # if member had no membership for that proj (approved or not)
  #  -> first membership in query, 0 if no memberships exist
  # if current is not approved, but 1+ other memberships are
  #  -> first approved membership in query

  #resulting request vars
  # .membership_status
  #   0 = no member object
  #   1 = no membership objects assoc w/member
  #   2 = no approved memberships
  #   3 = approved :) (current was, or current was changed -> is now)
  # .member - present in 1-3
  # .membership - present in 2-3

  def process_view(self, request, view_func, view_args, view_kwargs):
    #logger.debug('fund middleware running for ' + str(view_func.__module__))
    if 'fund' in view_func.__module__:
      if request.user.is_authenticated():
        request.membership_status = 0
        request.membership = None

        try:
          member = models.Member.objects.get(email=request.user.username) #q3
          #logger.info(member)
        except models.Member.DoesNotExist: #no member object
          logger.warning('Custom middleware: No member object with email of '+request.user.username)
          return None

        try: # get current membership
          membership = models.Membership.objects.select_related().get(member = member, pk=member.current) #q4
          request.membership_status = 3
          request.membership = membership
          logger.info(membership)
        except models.Membership.DoesNotExist: #current is wrong
          all = member.membership_set.all()
          if all: #if 1+ memberships, update current & set ship var
            logger.warning('Custom middleware: Current was wrong even though memberships exist')
            request.membership_status = 3
            request.membership = all[0] ###
            membership = all[0]
            member.current = membership.pk
            member.save()
          else: #no memberships
            logger.info('%s (no memberships)')
            member.current = 0
            member.save()
            request.membership_status = 1
            return None

        #membership exists, status is 3
        if membership.approved == False: #current not approved
          logger.warning('Current membership not approved')
          ships = member.membership_set.filter(approved=True)
          if ships: #switch default to their first approved gp
            request.membership_status = 3
            request.membership = ships[0]
            member.current = membership.pk
            member.save()
          else: #no approved GPs
            request.membership_status = 2
      else:
        request.membership_status = -1 #not logged in
    return None

