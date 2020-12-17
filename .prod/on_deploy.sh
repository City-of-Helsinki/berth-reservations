#!/bin/sh
# Runs migration scripts on each deployment
python /app/manage.py migrate --noinput

# Admin commands that need to be ran for each env can be added here
python /app/manage.py fix_broken_contracts
