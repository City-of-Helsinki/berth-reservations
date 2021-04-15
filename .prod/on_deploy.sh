#!/bin/sh

# Runs migration scripts on each deployment
python /app/manage.py migrate --noinput

# Updates group permissions on each deployment in case of updated permissions
python /app/manage.py set_group_model_permissions
