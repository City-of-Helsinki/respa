[![Stories in Ready](https://badge.waffle.io/City-of-Helsinki/respa.png?label=ready&title=Ready)](https://waffle.io/City-of-Helsinki/respa)
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
