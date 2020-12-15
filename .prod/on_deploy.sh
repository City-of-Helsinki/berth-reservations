#!/bin/sh
# Runs migration scripts on each deployment
python /app/manage.py migrate --noinput

# Admin commands that need to be ran for each env can be added here
python /app/manage.py loaddata berth_products.json
python /app/manage.py loaddata helsinki-harbor-resources.json
python /app/manage.py generate_missing_contracts
