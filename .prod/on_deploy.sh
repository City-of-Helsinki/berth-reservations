#!/bin/sh

# Runs migration scripts on each deployment
# TODO: Temporarily disable the automatic migrations since, on this case,
#  some commands need to be executed before the migration,
#  and those commands will be executed manually ONCE
# python /app/manage.py migrate --noinput

# Updates group permissions on each deployment in case of updated permissions
# python /app/manage.py set_group_model_permissions
