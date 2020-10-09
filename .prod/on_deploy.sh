#!/bin/sh
# Runs migration scripts on each deployment
exec python /app/manage.py migrate --noinput

