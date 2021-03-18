#!/bin/sh

# Runs migration scripts on each deployment
python /app/manage.py migrate --noinput

# TODO: Only has to be run once
python /app/manage.py harbors_connect_to_resources