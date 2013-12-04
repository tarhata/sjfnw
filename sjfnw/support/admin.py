from django.contrib import admin
from django.utils import timezone
from django.utils.safestring import mark_safe

from sjfnw.support.models import Guide


class GuideA(admin.ModelAdmin):
  list_display = ('title', 'display_contents', 'updated', 'updated_by')
  fields = ('title', 'contents')

  ordering = ('title',)

  def save_model(self, request, obj, form, change):
    obj.updated = timezone.now()
    obj.updated_by = request.user.username
    obj.save()

  def display_contents(self, obj):
    if obj.pk: # safety check
      return mark_safe(obj.contents.replace('\n', '<br>'))

admin.site.register(Guide, GuideA)

