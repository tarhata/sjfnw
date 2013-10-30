coverage run --source='.' --include='sjfnw/*' --omit='*tests.py,*__init__.py,*commands/*' manage.py test fund grants
coverage report
