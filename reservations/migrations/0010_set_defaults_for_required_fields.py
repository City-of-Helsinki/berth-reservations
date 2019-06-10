# Generated by Django 2.2 on 2019-05-16 09:50
from decimal import Decimal

from django.db import migrations


def set_defaults_for_nullable_fields(apps, schema_editor):
    BerthReservation = apps.get_model("reservations", "BerthReservation")
    WinterStorageReservation = apps.get_model(
        "reservations", "WinterStorageReservation"
    )

    for r in BerthReservation.objects.filter(boat_length__isnull=True):
        r.boat_length = Decimal("0")
        r.save()

    for r in BerthReservation.objects.filter(boat_width__isnull=True):
        r.boat_width = Decimal("0")
        r.save()

    for r in WinterStorageReservation.objects.filter(boat_length__isnull=True):
        r.boat_length = Decimal("0")
        r.save()

    for r in WinterStorageReservation.objects.filter(boat_width__isnull=True):
        r.boat_width = Decimal("0")
        r.save()


class Migration(migrations.Migration):

    dependencies = [("reservations", "0009_add_winter_storage_reservations")]

    operations = [
        migrations.RunPython(
            set_defaults_for_nullable_fields, migrations.RunPython.noop
        )
    ]
