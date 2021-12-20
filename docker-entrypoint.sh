#!/bin/bash

set -e

# Wait for the database to be available, TODO configurable port also
if [ -z "$SKIP_DATABASE_CHECK" -o "$SKIP_DATABASE_CHECK" = "0" ]; then
  until nc -z -v -w30 "$DATABASE_HOST" "5432"
  do
    echo "Waiting for postgres database connection..."
    sleep 1
  done
  echo "Database is up!"
fi

# Apply database migrations
if [[ "$APPLY_MIGRATIONS" = "1" ]]; then
    echo "Applying database migrations..."
    python ./manage.py migrate --noinput
fi

# Check that there are no pending migrations to generate
if [[ "$CHECK_MIGRATIONS" = "1" ]]; then
  echo "Checking database migrations..."
  python ./manage.py makemigrations --verbosity 3 --dry-run --noinput --check
fi

if [[ "$CREATE_SUPERUSER" = "1" ]]; then
  python ./manage.py add_admin_user -u admin -p adminpass -e admin@example.com
  echo "Admin user created with credentials admin:adminpass (email: admin@example.com)"
fi

python ./scripts/load_notification_templates.py
echo "Notification templates loaded"

# Start server
if [[ ! -z "$@" ]]; then
    "$@"
elif [[ "$DEV_SERVER" = "1" ]]; then
    python -Wd ./manage.py runserver 0.0.0.0:8000
else
    python ./manage.py collectstatic --noinput
    uwsgi --ini .prod/uwsgi.ini
fi
