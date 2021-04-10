#!/bin/bash

echo "NOTICE: Start the uwsgi web server"
exec uwsgi --http :8000 --wsgi-file deploy/wsgi.py --static-map /static=/usr/src/app/static --static-map /media=/usr/src/app/www/media --log-master -p 10 -T --master --listen 2048 --static-gzip-all

# variables: port, media root, -p for processes, --listen for listening connections
