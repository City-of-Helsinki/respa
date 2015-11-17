[![Stories in Ready](https://badge.waffle.io/City-of-Helsinki/respa.png?label=ready&title=Ready)](https://waffle.io/City-of-Helsinki/respa)
[![Build Status](https://api.travis-ci.org/City-of-Helsinki/respa.svg?branch=master)](https://travis-ci.org/City-of-Helsinki/respa)
[![Coverage Status](https://coveralls.io/repos/City-of-Helsinki/respa/badge.svg?branch=master&service=github)](https://coveralls.io/github/City-of-Helsinki/respa?branch=master)

respa – Resource reservation and management service
===================

Installation
------------

1. Create the database.

```shell
sudo -u postgres createuser -L -R -S respa
sudo -u postgres psql -d template1 -c "create extension hstore;"
sudo -u postgres createdb -Orespa respa
sudo -u postgres psql respa -c "CREATE EXTENSION postgis;"
```

2. Run Django migrations and import data

```shell
python manage.py migrate
python manage.py createsuperuser  # etc...
python manage.py resources_import --all tprek
python manage.py resources_import --all kirjasto10
python manage.py resources_import --all kirjastot
```

3. Ready to roll!

h3. Setting up PostGIS/GEOS/GDAL on Windows (x64) / Python 3

* Install PGSQL from http://get.enterprisedb.com/postgresql/postgresql-9.4.5-1-windows-x64.exe
  * At the end of installation, agree to run Stack Builder and have it install the PostGIS bundle
* Install OSGeo4W64 from http://download.osgeo.org/osgeo4w/osgeo4w-setup-x86_64.exe
  * The defaults should do
* Add the osgeo4w64 bin path to your PATH
  * Failing to do this while setting `GEOS_LIBRARY_PATH`/`GDAL_LIBRARY_PATH` will result in
    "Module not found" errors or similar, which can be annoying to track down.

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

Respa uses two files for requirements. The workflow is as follows.

requirements.txt is not edited manually, but is generated
with 'pip freeze -lr plain-requirements.txt'.

requirements.txt always contains fully tested versions of
the requirements, including their dependencies as output
by pip freeze.

plain-requirements.txt contains the primary requirements
of the project, without version numbers and without their
dependencies.

In production, deployments should always use requirements.txt
and the versions pinned therein. In development, new virtualenvs
and development environments should also be initialised using
requirements.txt.

In development and testing, to check for new versions
of requirements, use the command 'pip-review' or requires.io.

To update ​*all*​ of the requirements to the latest versions
with a single command, use

   pip install -U -r plain-requirements.txt

After verifying that they work and optionally downgrading
some dependencies, run pip freeze.

To add a dependency, add it to plain-requirements.txt and
run 'pip install -r plain-requirements.txt'.

To remove a dependency, remove it from plain-requirements.txt
and run 'pip uninstall <NAME-OF-DEPENDENCY>'.

Important! After all changes, verify & test them, then run
'pip freeze -lr plain.requirements.txt >requirements.txt'.
Commit the changes.
