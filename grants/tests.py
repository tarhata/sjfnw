from django.test import TestCase
from grants import models
from django.test import TestCase
from django.contrib.auth.models import User
import sys

def setPaths():
  #add libs to the path that dev_appserver normally takes care of
  sys.path.append('C:\Program Files (x86)\Google\google_appengine\lib\yaml\lib')
  sys.path.append('C:\Program Files (x86)\Google\google_appengine\lib\webob_1_1_1')

def logInTesty(self):
  user = User.objects.create_user('testacct@gmail.com', 'testacct@gmail.com', 'testy')
  self.client.login(username = 'testacct@gmail.com', password = 'testy')

""" TESTS TO DO
      discard draft button
      submitted apps sorting
      password reset on live
      file upload/serving? 
      loading app page for the first time
      brand new org
      org with profile info saved """

class GrantApplicationTests(      
  
  #just copied from stackoverflow, needs work
  def test_a_file(self):
    import tempfile
    import os
    filename = tempfile.mkstemp()[1]
    f = open(filename, 'w')
    f.write('These are the file contents')
    f.close()
    f = open(filename, 'r')
    post_data = {'file': f}
    response = self.client.post('/apply/4/', post_data)
    f.close()
    os.remove(filename)
    self.assertTemplateUsed(response, 'tests/solution_detail.html')
    self.assertContains(response, os.path.basename(filename))
    
    
    
TEPOST_DICTS = [
  valid =  {u'website': [u'asdfsdaf'],
            u'mission': [u'A kmission statement of some importance!'],
            u'founded': [u'351'],
            u'fiscal_telephone': [u''],
            u'email_address': [u'as@gmail.com'],
            u'city': [u'sdaf'],
            u'amount_requested': [u'100000'],
            u'zip': [u'654'],
            u'start_year': [u'sdfsadfdsf'],
            u'project_budget': [u''],
            u'grant_cycle': [u'2'],
            u'support_type': [u'General support'],
            u'state': [u'OR'],
            u'fiscal_org': [u''],
            u'status': [u'501c3'],u'narrative1': [u'adasrdsadssdfsdfsdfsdfdfsdfsdfdfsdfsdf\r\r\ndfsdfsdfdfsdfsdfdfsdfsdfdfsdfsdfsdfsdfdfsdfsdfdfsdfsdfdfsdfsdfdfdfsdfdfsdfsdfdfsdfsdfdfdfsdfsdfdfsdfsdfdfsdfsdf'],
            u'narrative2': [u'sdfsdfsdfitizes groups that understand and address the underlying, or root causes of the issues, and that bring people together to build collective power.\r\r\nWhat problems, needs or issues does your work address?\r\r\nWhat are the root causes of these'],
            u'narrative3': [u'sdfasfsdfsdfdsfdsfsdffsdfitizes groups that understand and address the underlying, or root causes of the issues, and that bring people together to build collective power.\r\r\nWhat problems, needs or issues does your work address?\r\r\nWhat are theroot causes of thesefdsfsdfsdfsdfsdfsdfsdfsdfds'],
            u'narrative4': [u'itizes groups that understand and address the underlying, or root causes of the issues, and that bring people together to build collective power.\r\r\nWhat problems, needs or issues does your work address?\r\r\nWhat are the root causes of theseitizesgroups that understand and address the underlying, or root causes of the issues, and that bring people together to build collective power.\r\r\nWhat problems, needs or issues does your work address?\r\r\nWhat are the root causes of these'],
            u'narrative5': [u'itizes groups that understand and address the underlying, orroot causes of the issues, and that bring people together to build collective power.\r\r\nWhat problems, needs or issues does your work address?\r\r\nWhat are the root causes of theseitizes groups that understand and address the underlying, or root causes of the issues, and that bring people together to build collective power.\r\r\nWhat problems, needs or issues does your work address?\r\r\nWhat are the root causes of these'],
            u'fax_number': [u'321'],
            u'budget_last': [u'256161'],
            u'address': [u'asdfsdf'],
            u'fiscal_email': [u''],
            u'grant_period': [u'sdfgsdfdsaf'],
            u'previous_grants': [u'dsfsadfsfdsa dsg gdfg sadfdsg fd g'],
            u'grant_request': [u'A grant rewuireasjdflsdfasdg'],
            u'fiscal_person': [u''],
            u'project_title': [u''],
            u'budget_current': [u'62561'],
            u'fiscal_address': [u''],
            u'telephone_number': [u'325'],
            u'organization': [u'1'],
            u'contact_person': [u'asdfsadfasdfasdf'],
            u'ein': [u'654']}