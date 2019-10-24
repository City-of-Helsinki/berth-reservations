# -*- coding: utf-8 -*-
"""
This script:

1) fakes initial migration for the new 'users' app.
It is needed, because using Django's '--fake-initial' flag does
not work with the apps tha introduce a custom user model to the project.

Inspired by the first answer to this ticket:
https://code.djangoproject.com/ticket/28250

2) updates 'django_content_type' table with the new app label
"""
import os
import sys

import django
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def fake_initial_users_migrations():
    recorder = MigrationRecorder(connection)
    recorder.record_applied("users", "0001_initial")


def update_content_types():
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE django_content_type SET app_label = 'users'"
            "WHERE app_label = 'auth' AND model = 'user'"
        )


if __name__ == "__main__":
    sys.path.append(PROJECT_ROOT)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "berth_reservations.settings")

    django.setup()

    fake_initial_users_migrations()

    update_content_types()
