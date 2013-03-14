from django.db import models
from django.forms import ModelForm
from django.forms.widgets import RadioSelect, HiddenInput
from sjfnw.grants.models import GrantApplication
from sjfnw.fund.models import Membership

class ApplicationRating(models.Model):

  application = models.ForeignKey(GrantApplication)
  membership = models.ForeignKey(Membership)
  submitted = models.BooleanField(default=False)
  
  program = models.DecimalField(decimal_places = 2, max_digits = 3, null=True, blank=True)
  diversity = models.DecimalField(decimal_places = 2, max_digits = 3, null=True, blank=True)
  soundness = models.DecimalField(decimal_places = 2, max_digits = 3, null=True, blank=True)
  lack_of_access = models.DecimalField(decimal_places = 2, max_digits = 3, null=True, blank=True)
  collaboration = models.DecimalField(decimal_places = 2, max_digits = 3, null=True, blank=True)
  
  comments = models.TextField()
  
  submission_time = models.DateTimeField(auto_now_add=True) #FIX
  def __unicode__(self):
	return ("Program" + self.program + "\nDiversity" + self.diversity + "\nSoundness" + self.soundness + "\nLack of Access" + self.lack_of_access + "\nCollaboration" + self.collaboration) 
  def total(self):
	if scoring_bonus_poc or scoring_bonus_geo:
		return (1.1*self.program*7+self.diversity*5+self.soundness*4+self.lack_of_access*2+self.collaboration*2)
	
	return (self.program*7+self.diversity*5+self.soundness*4+self.lack_of_access*2+self.collaboration*2)

class RatingForm(ModelForm):
  class Meta:
    model = ApplicationRating
    exclude = ('submission_time')
    # fields = ('comments', 'program', 'diversity', 'soundness', 'lack_of_access', 'collaboration')
    widgets = {
      'program': RadioSelect(attrs={'class': 'grader_radio_button'}),
      'diversity': RadioSelect(attrs={'class': 'grader_radio_button'}),
      'soundness': RadioSelect(attrs={'class': 'grader_radio_button'}),
      'lack_of_access': RadioSelect(attrs={'class': 'grader_radio_button'}),
      'collaboration': RadioSelect(attrs={'class': 'grader_radio_button'}),
      'application': HiddenInput(),
      'membership': HiddenInput(),
    }
