#!/bin/bash

echo "NOTICE: Get static files for serving"
./manage.py collectstatic --no-input

echo "NOTICE: Start the gunicorn web server"
gunicorn --access-logfile - --error-logfile - -b 0.0.0.0:8000 deploy.wsgi
