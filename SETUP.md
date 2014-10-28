This will go over installation, running a local server and running tests.

### Installation
Instructions assume you're running linux or mac osx and can use a package manager as needed - homebrew, apt-get, etc.

#### Python 2.7x & git
Should come installed with your OS.  Confirm with `python --version` and `git --version` and install/update if needed.

#### [Google App Engine SDK](https://cloud.google.com/appengine/downloads#Google_App_Engine_SDK_for_Python) (includes Django)

Download & unzip. Update your `~/.bashrc`:
```
export PATH=$PATH:/[path to gae]`
export PYTHONPATH=$PYTHONPATH:[path to gae]
export PYTHONPATH=$PYTHONPATH:[path to gae]/lib/yaml/lib
export PYTHONPATH=$PYTHONPATH:[path to gae]/lib/webob-1.2.3
```

#### MySQL

Install **mysql-server** and **python-mysqldb**. When prompted, enter the password used in sjfnw/settings.py under database.

Once those have installed, create the database:

1. `mysql -uroot -p` to get into the mysql shell. This will prompt you for pw you set when you installed.
2. `create database sjfdb_local;`

## Running a local server

The first time, or after adding new models, you'll need to sync the database first. From root level of the repo, run:

`./manage.py syncdb`

You should see output as tables are created in the local database.
Create a superuser when prompted - that creates a User account that you can use to log into the admin site on your local server.

_If this doesn't work, make sure `manage.py` has execute permissions. `chmod a+x manage.py` should work._

##### To run the server:

Move up one level to the directory containing the repo and run:

`dev_appserver.py sjfnw`

_If you get something like 'command not found', make sure GAE is in your path. Use `echo $PATH` to confirm._

## Running tests

`./manage.py test fund grants`

