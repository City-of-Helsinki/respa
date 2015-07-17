#!/usr/bin/env python
"""
HACK to support the Django + nose without django-nose.

Built based on documentation from:
* https://docs.djangoproject.com/en/1.8/topics/testing/advanced/#using-the-django-test-runner-to-test-reusable-applications
* http://nose.readthedocs.org/en/latest/usage.html#basic-usage
"""
import sys

import django
import nose
from django.test.utils import setup_test_environment, teardown_test_environment
from django.db import connection


if __name__ == '__main__':
    django.setup()

    try:
        sys.argv.remove('--keepdb')
    except ValueError:
        keepdb = False
    else:
        keepdb = True

    setup_test_environment()
    test_db_name = connection.creation.create_test_db(keepdb=keepdb)
    result = nose.run()
    connection.creation.destroy_test_db(test_db_name, keepdb=keepdb)
    teardown_test_environment()
    if not result:
        sys.exit(1)
