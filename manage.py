#!/usr/bin/env python
import os
import sys
import logging

if __name__ == "__main__":
  os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sjfnw.settings")

  from django.core.management import execute_from_command_line

  #test setup - hacky?
  sys.path.append(os.path.dirname(__file__) + '/sjfnw') #for windows, use '\\sjfnw' instead
  sys.path.append('/home/aisa/Devel/google_appengine/lib/webob-1.2.3')
  #fr = logging.Formatter(fmt='%(levelname)-8s %(asctime)s %(filename)s:%(lineno)d %(funcName)s]: %(message)s')
  logging.basicConfig(format='%(levelname)-8s %(asctime)s %(filename)s:%(lineno)d %(funcName)s]: %(message)s', 
      datefmt = '%Y-%m-%d %H:%M:%S')
  #logging.getLogger().handlers[0].setFormatter(fr)

  #print("\n".join(sys.path))

  execute_from_command_line(sys.argv)
