#!/bin/sh
# Runs database initialization scripts on first install only, disabled for now as staging and prod are already seeded
python /app/manage.py migrate --noinput
python /app/manage.py geo_import finland --municipalities
python /app/manage.py geo_import helsinki --divisions
python /app/manage.py loaddata helsinki-ws-resources.json
python /app/manage.py loaddata helsinki-harbor-resources.json
python /app/manage.py loaddata helsinki-harbor-resources-fixes-2021-06-11.json
python /app/manage.py assign_area_regions
python /app/manage.py loaddata switch-reasons.json
python /app/manage.py loaddata groups.json
python /app/manage.py set_group_model_permissions
python /app/manage.py loaddata berth_products.json
