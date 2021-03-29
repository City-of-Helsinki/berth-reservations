#!/bin/sh

# Runs migration scripts on each deployment
python /app/manage.py migrate --noinput

