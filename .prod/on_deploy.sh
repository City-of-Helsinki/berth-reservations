#!/bin/sh

# Runs migration scripts on each deployment
python /app/manage.py migrate --noinput

# Berth customers group added 2021-05, this line can be removed after prod deployment done successfully
python /app/manage.py loaddata groups.json

# Updates group permissions on each deployment in case of updated permissions
python /app/manage.py set_group_model_permissions
