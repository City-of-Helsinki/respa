Respa-Exchange
==============


A connector for bidirectional synchronization of [Respa][respa]
event information with Microsoft Exchange resource calendars.

Installation
------------

Respa-Exchange is a Django app that hooks to Respa using Django signals.

* Add `respa_exchange` to your `INSTALLED_APPS`.
* Run Django `migrate` and restart your app server, etc.
* You should now see Respa-Exchange entries in the Django admin.

Development/howto
-----------------

You'll need a copy of [Respa][respa] to develop Respa-Exchange against.

* Set up a virtualenv.
* Install Respa's requirements: `pip install -r requirements.txt`
* Run `py.test`. Everything should work.

Requirements
------------

* Microsoft Exchange On-Premises installation with
  Exchange Web Services enabled
  
Acknowledgements
----------------

* [LinkedIn's PyExchange][pyex] project was a tremendous help. Thanks!

---

[respa]: https://github.com/City-of-Helsinki/respa
[pyex]: https://github.com/linkedin/pyexchange
