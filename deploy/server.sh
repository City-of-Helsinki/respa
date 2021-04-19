#!/bin/sh

./deploy/init.sh

exec uwsgi
