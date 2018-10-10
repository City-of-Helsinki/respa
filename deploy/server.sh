#!/bin/bash

echo "NOTICE: Get static files for serving"
./manage.py collectstatic --no-input

echo "NOTICE: Start the uwsgi web server"
uwsgi --http :8080 --wsgi-file deploy/wsgi.py --check-static /usr/src/app/www
