#!/bin/bash

echo "NOTICE: Get static files for serving"
./manage.py collectstatic --no-input

# exec uwsgi --http :8000 --wsgi-file deploy/wsgi.py --check-static /usr/src/app/www

echo "NOTICE: Start the uwsgi web server"
exec uwsgi --http :8000 --wsgi-file deploy/wsgi.py --static-map /media=/usr/src/app/www/media --log-master -p 10 -T --master --listen 2048

# variables: port, media root, -p for processes, --listen for listening connections
