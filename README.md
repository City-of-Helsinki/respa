[![Stories in Ready](https://badge.waffle.io/City-of-Helsinki/respa.png?label=ready&title=Ready)](https://waffle.io/City-of-Helsinki/respa)
[![Build Status](https://api.travis-ci.org/City-of-Helsinki/respa.svg?branch=master)](https://travis-ci.org/City-of-Helsinki/respa)
[![codecov](https://codecov.io/gh/City-of-Helsinki/respa/branch/master/graph/badge.svg)](https://codecov.io/gh/City-of-Helsinki/respa)

respa – Resource reservation and management service
===================

Installation
------------

### Prepare virtualenv

     virtualenv -p /usr/bin/python3 ~/.virtualenvs/
     workon respa

### Install required packages

Install all required packages with pip command:

     pip install -r requirements.txt

### Create the database

```shell
sudo -u postgres createuser -L -R -S respa
sudo -u postgres psql -d template1 -c "create extension hstore;"
sudo -u postgres createdb -Orespa respa
sudo -u postgres psql respa -c "CREATE EXTENSION postgis;"
```

### Run Django migrations and import data

```shell
python manage.py migrate
python manage.py createsuperuser  # etc...
python manage.py geo_import --municipalities finland
python manage.py geo_import --divisions helsinki
python manage.py resources_import --all tprek
python manage.py resources_import --all kirjastot
```

### Settings
- `RESPA_IMAGE_BASE_URL`: Base URL used when building image URLs in email notifications. Example value: `'https://api.hel.fi/respa/'`.

- *TODO* document rest of relevant settings.

Ready to roll!

### Setting up PostGIS/GEOS/GDAL on Windows (x64) / Python 3

* Install PGSQL from http://get.enterprisedb.com/postgresql/postgresql-9.4.5-1-windows-x64.exe
  * At the end of installation, agree to run Stack Builder and have it install the PostGIS bundle
* Install OSGeo4W64 from http://download.osgeo.org/osgeo4w/osgeo4w-setup-x86_64.exe
  * The defaults should do
* Add the osgeo4w64 bin path to your PATH
  * Failing to do this while setting `GEOS_LIBRARY_PATH`/`GDAL_LIBRARY_PATH` will result in
    "Module not found" errors or similar, which can be annoying to track down.


Production considerations
-------------------------

### Respa Exchange sync

Respa supports synchronizing reservations with Exchange resource mailboxes (calendars). You can run the sync either manually through `manage.py respa_exchange_download`, or you can set up a listener daemon with `manage.py respa_exchange_listen_notifications`.

If you're using UWSGI, you can set up the listener as an attached daemon:

```yaml
uwsgi:
  attach-daemon2: cmd=/home/respa/run-exchange-sync.sh,pidfile=/home/respa/exchange_sync.pid,reloadsignal=15,touch=/home/respa/service_state/touch_to_reload
```

The helper script `run-exchange-sync.sh` activates a virtualenv and starts the listener daemon:

```bash
#!/bin/sh

. $HOME/venv/bin/activate

cd $HOME/respa
./manage.py respa_exchange_listen_notifications --log-file=$HOME/logs/exchange_sync.log --pid-file=$HOME/exchange_sync.pid --daemonize
```

Running tests
-------------

Respa uses the [pytest](http://pytest.org/latest/) test framework.

To run the test suite,

```shell
$ py.test .
```

should be enough.

```shell
$ py.test --cov-report html .
```

to generate a HTML coverage report.


Requirements
------------

This project uses two files for requirements. The workflow is as follows.

`requirements.txt` is not edited manually, but is generated
with `pip-compile`.

`requirements.txt` always contains fully tested, pinned versions
of the requirements. `requirements.in` contains the primary, unpinned
requirements of the project without their dependencies.

In production, deployments should always use `requirements.txt`
and the versions pinned therein. In development, new virtualenvs
and development environments should also be initialised using
`requirements.txt`. `pip-sync` will synchronize the active
virtualenv to match exactly the packages in `requirements.txt`.

In development and testing, to update to the latest versions
of requirements, use the command `pip-compile`. You can
use [requires.io](https://requires.io) to monitor the
pinned versions for updates.

To remove a dependency, remove it from `requirements.in`,
run `pip-compile` and then `pip-sync`. If everything works
as expected, commit the changes.
