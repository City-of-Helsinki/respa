#!/bin/sh

# Scripts to run on first deploy

python manage.py migrate
python manage.py collectstatic --no-input

# Compress files in media root for Uwsgi

LOCAL_MEDIA="${MEDIA_ROOT:-media}"
python -m whitenoise.compress "${LOCAL_MEDIA}"
