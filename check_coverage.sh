coverage run --source='sjfnw' --omit='sjfnw/wsgi.py,sjfnw/mail.py,*/tests.py,*__init__.py,*commands/*' manage.py test grants fund
coverage report
