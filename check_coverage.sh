coverage run --source='sjfnw' --omit='sjfnw/wsgy.py,sjfnw/mail.py,*/tests.py,*__init__.py,*commands/*' manage.py test grants fund
coverage report
