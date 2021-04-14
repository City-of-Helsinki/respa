#!/bin/sh

# Scripts to run from time to time

# Compress files in media root for Uwsgi

LOCAL_MEDIA="${MEDIA_ROOT:-media}"
python -m whitenoise.compress "${LOCAL_MEDIA}"
