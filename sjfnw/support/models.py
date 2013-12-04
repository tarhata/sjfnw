from django.db import models
from django.utils import timezone

class Guide(models.Model):

  created = models.DateTimeField(blank=True, default=timezone.now())
  created_by = models.CharField(max_length=100)
  updated = models.DateTimeField(blank=True, default=timezone.now())
  updated_by = models.CharField(max_length=100)

  title = models.CharField(max_length=255)
  contents = models.TextField()

  def __unicode__(self):
    return self.title

