# -*- coding: utf-8 -*-
"""
This script:

1) updates 'django_content_type' table with the new app label
2) renames all the tables from 'reservations_xxx' to 'applications_xxx' to match the new app name
3) renames the existing migrations from 'reservations' to 'applications'
"""
import os
import sys

import django
from django.db import connection, transaction

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

TABLES = [
    ("reservations_berthapplication", "applications_berthapplication"),
    ("reservations_berthswitch", "applications_berthswitch"),
    ("reservations_berthswitchreason", "applications_berthswitchreason"),
    ("reservations_harborchoice", "applications_harborchoice"),
    (
        "reservations_winterstorageapplication",
        "applications_winterstorageapplication",
    ),
    ("reservations_winterstorageareachoice", "applications_winterstorageareachoice"),
]


def update_content_types():
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE django_content_type SET app_label = 'reservations'"
            "WHERE app_label = 'applications'"
        )


def update_table_name(old_table_name, new_table_name):
    with connection.cursor() as cursor:
        cursor.execute(f"ALTER TABLE {old_table_name} RENAME TO {new_table_name}")


def update_migration_table():
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE django_migrations SET app='applications' WHERE app='reservations'"
        )


if __name__ == "__main__":
    sys.path.append(PROJECT_ROOT)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "berth_reservations.settings")

    django.setup()

    with transaction.atomic():
        update_content_types()

        for old_name, new_name in TABLES:
            update_table_name(old_name, new_name)

        update_migration_table()
