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
    ./manage.py migrate --noinput
fi


if [[ "$CREATE_SUPERUSER" = "1" ]]; then
python ./manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(email='admin@example.com').delete(); User.objects.create_superuser('admin', 'admin@example.com', 'adminpass')"
 echo "Admin user created with credentials admin:adminpass (email: admin@example.com)"
fi

# Start server
if [[ ! -z "$@" ]]; then
    "$@"
elif [[ "$DEV_SERVER" = "1" ]]; then
    python ./manage.py runserver 0.0.0.0:8000
else
    python ./manage.py collectstatic --noinput
    uwsgi --ini .prod/uwsgi.ini
fi