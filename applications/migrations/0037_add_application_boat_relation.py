# Generated by Django 3.2.8 on 2021-11-09 15:59
from itertools import chain

from django.db import migrations, models
import django.db.models.deletion

OTHER_BOAT_TYPE_ID = 9


def populate_application_boat(apps, schema_editor):
    BerthApplication = apps.get_model("applications", "BerthApplication")
    WinterStorageApplication = apps.get_model(
        "applications", "WinterStorageApplication"
    )
    Boat = apps.get_model("customers", "Boat")

    for application in sorted(
        chain(BerthApplication.objects.all(), WinterStorageApplication.objects.all()),
        key=lambda a: a.created_at,
    ):

        def prop_or_none(prop):
            value = getattr(application, prop, None)
            if value == 0:
                value = None
            return value

        boat = None

        if application.customer and application.boat_registration_number:
            try:
                # Use an existing Boat if there is exactly one that matches with the
                # application's customer and registration number
                boat = Boat.objects.get(
                    owner=application.customer,
                    registration_number=application.boat_registration_number,
                )
            except (Boat.DoesNotExist, Boat.MultipleObjectsReturned):
                pass

        if not boat:
            # If there is no exact match a new Boat will be created
            boat = Boat(
                owner=application.customer,
                registration_number=application.boat_registration_number,
            )

        boat_data = {
            "boat_type_id": application.boat_type_id or OTHER_BOAT_TYPE_ID,
            "length": application.boat_length,
            "width": application.boat_width,
            "registration_number": getattr(application, "boat_registration_number", ""),
            "name": getattr(application, "boat_name", ""),
            "model": getattr(application, "boat_model", ""),
            "draught": prop_or_none("boat_draught"),
            "weight": prop_or_none("boat_weight"),
            "propulsion": getattr(application, "boat_propulsion", ""),
            "hull_material": getattr(application, "boat_hull_material", ""),
            "intended_use": getattr(application, "boat_intended_use", ""),
            "is_inspected": prop_or_none("boat_is_inspected"),
            "is_insured": prop_or_none("boat_is_insured"),
        }
        for key, value in boat_data.items():
            setattr(boat, key, value)

        boat.save()

        # use queryset.update() instead of instance.save() to avoid creating a change entry
        type(application).objects.filter(pk=application.pk).update(boat=boat)


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0017_make_boat_owner_nullable"),
        ("applications", "0036_add_application_change_list"),
    ]

    operations = [
        migrations.AddField(
            model_name="berthapplication",
            name="boat",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="customers.boat",
                verbose_name="boat",
            ),
        ),
        migrations.AddField(
            model_name="winterstorageapplication",
            name="boat",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="customers.boat",
                verbose_name="boat",
            ),
        ),
        migrations.RunPython(populate_application_boat, migrations.RunPython.noop),
    ]
