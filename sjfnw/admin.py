from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType

import logging
logger = logging.getLogger('sjfnw')


# SHARED

class YearFilter(admin.SimpleListFilter):
  """ Reusable filter by year.  See __init__ """
  title = 'year'
  parameter_name = 'year'
  filter_model = None
  field = ''
  intermediate = ''

  def lookups(self, request, model_admin):
    dates = self.filter_model.objects.values_list(self.field, flat=True
                                         ).order_by('-%s' % self.field)
    prev = None
    years = []
    for date in dates:
      if date.year != prev:
        years.append((date.year, date.year))
        prev = date.year
    logger.info(years)
    return years

  def queryset(self, request, queryset):
    val = self.value()
    if not val:
      return queryset
    try:
      year = int(val)
    except:
      logger.error('YearFilter received invalid value %s' % val)
      messages.error(request,
          'Error loading filter. Contact techsupport@socialjusticefund.org')
      return queryset
    else:
      filt = {}
      filt['%s__%s__year' % (self.intermediate, self.field)] = year
      return queryset.filter(**filt)



# REGISTER

advanced_admin = AdminSite(name='advanced')

admin.site.unregister(Group)

advanced_admin.register(User, UserAdmin)
advanced_admin.register(Group)
advanced_admin.register(Permission)
advanced_admin.register(ContentType)

