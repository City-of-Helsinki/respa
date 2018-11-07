[![Stories in Ready](https://badge.waffle.io/City-of-Helsinki/respa.png?label=ready&title=Ready)](https://waffle.io/City-of-Helsinki/respa)
[![Build Status](https://api.travis-ci.org/City-of-Helsinki/respa.svg?branch=master)](https://travis-ci.org/City-of-Helsinki/respa)
[![codecov](https://codecov.io/gh/City-of-Helsinki/respa/branch/master/graph/badge.svg)](https://codecov.io/gh/City-of-Helsinki/respa)

respa – Resource reservation and management service
===================
Respa is a backend service for reserving and managing resources (e.g. meeting rooms, equipment, personnel). The open two-way REST API is interoperable with the [6Aika Resource reservation API specification](https://github.com/6aika/api-resurssienvaraus) created by the six largest cities in Finland. You can explore the API at [api.hel.fi](https://api.hel.fi/respa/v1/) and view the API documentation at [dev.hel.fi](https://dev.hel.fi/apis/respa/).

User interfaces for Respa developed by the City of Helsinki are [Varaamo](https://github.com/City-of-Helsinki/varaamo) and [Huvaja](https://github.com/City-of-Helsinki/huvaja), and the now-defunct [Stadin Tilapankki](https://github.com/City-of-Helsinki/tilapankki). The City of Hämeenlinna has developed a [Berth Reservation UI](https://github.com/CityOfHameenlinna/hmlvaraus-frontend) and [backend](https://github.com/CityOfHameenlinna/hmlvaraus-backend) on top of Respa.

Editing data can be done by using a simple UI based on Django admin.

Used by
------------

- [City of Helsinki](https://api.hel.fi/respa/v1/) - for [Varaamo UI](https://varaamo.hel.fi/) & [Huvaja UI](https://huonevaraus.hel.fi/)
- [City of Espoo](https://api.hel.fi/respa/v1/) - for [Varaamo UI](https://varaamo.espoo.fi/)
- [City of Vantaa](https://api.hel.fi/respa/v1/) - for [Varaamo UI](https://varaamo.vantaa.fi/)
- [City of Oulu](https://varaamo-api.ouka.fi/v1/) - for [Varaamo UI](https://varaamo.ouka.fi/)
- [City of Mikkeli](https://mikkeli-respa.metatavu.io/v1/) - for [Varaamo UI](https://varaamo.mikkeli.fi/)
- [City of Tampere](https://respa.tampere.fi/v1/) - for [Varaamo UI](https://varaamo.tampere.fi/)
- City of Hämeenlinna - for [Berth Reservation UI](https://varaukset.hameenlinna.fi/)

FAQ
------------

### Why is it called Respa?
Short for "RESurssiPAlvelu" i.e. Resource Service.

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
- `RESPA_IMAGE_BASE_URL`: Base URL used when building image URLs in email notifications. Example value: `'https://api.hel.fi'`.

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

Creating sanitized database dump
--------------------------------

This project uses Django Sanitized Dump for database sanitation.  Issue
the following management command on the server to create a sanitized
database dump:

    ./manage.py create_sanitized_dump > sanitized_db.sql


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

Contributing
------------

Your contributions are always welcome! If you want to report a bug or see a new feature feel free to create a new [Issue](https://github.com/City-of-Helsinki/respa/issues/new) or discuss it with us on [Gitter](https://gitter.im/City-of-Helsinki/heldev). Alternatively, you can create a pull request (base master branch). Your PR will be reviewed by the project tech lead.

License
------------

Usage is provided under the [MIT License](https://github.com/City-of-Helsinki/respa/blob/master/LICENSE).
