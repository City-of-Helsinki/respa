[![Stories in Ready](https://badge.waffle.io/City-of-Helsinki/respa.png?label=ready&title=Ready)](https://waffle.io/City-of-Helsinki/respa)
[![Build Status](https://api.travis-ci.org/City-of-Helsinki/respa.svg?branch=master)](https://travis-ci.org/City-of-Helsinki/respa)
[![Coveralls](https://img.shields.io/coveralls/City-of-Helsinki/respa.svg)]()

respa – Resource reservation and management service
===================

Installation
------------

1. Create the database.

```shell
sudo -u postgres createuser -L -R -S respa
sudo -u postgres psql respa
  CREATE EXTENSION postgis;
```
