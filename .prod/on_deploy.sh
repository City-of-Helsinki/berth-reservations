#!/bin/sh
# Runs migration scripts on each deployment
python /app/manage.py migrate --noinput

# This can be removed once executed
python /app/manage.py assign_ws_lease_stickers
