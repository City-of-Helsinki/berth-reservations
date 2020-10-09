#!/bin/sh
# Runs database initialization scripts on first install only
python /app/manage.py migrate --noinput
python /app/manage.py geo_import finland --municipalities
python /app/manage.py geo_import helsinki --divisions
python /app/manage.py loaddata helsinki-harbors.json
python /app/manage.py loaddata helsinki-ws-resources.json
python /app/manage.py loaddata helsinki-winter-areas.json
python /app/manage.py loaddata helsinki-harbor-resources.json
python /app/manage.py assign_area_regions
python /app/manage.py loaddata switch-reasons.json
python /app/manage.py loaddata groups.json
python /app/manage.py set_group_model_permissions
