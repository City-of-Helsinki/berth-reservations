# Generated by Django 2.2.5 on 2019-10-07 12:17

import django.contrib.gis.db.models.fields
from django.db import migrations, models
import django.db.models.deletion
import enumfields.fields
import parler.models
import resources.enums
import resources.models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [("munigeo", "0004_delete_old_translations")]

    operations = [
        migrations.CreateModel(
            name="AvailabilityLevel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                )
            ],
            options={
                "verbose_name": "availability level",
                "verbose_name_plural": "availability levels",
                "ordering": ("id",),
            },
            bases=(parler.models.TranslatableModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="BoatType",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                )
            ],
            options={
                "verbose_name": "boat type",
                "verbose_name_plural": "boat types",
                "ordering": ("id",),
            },
            bases=(parler.models.TranslatableModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="Harbor",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "servicemap_id",
                    models.CharField(
                        blank=True,
                        help_text="ID in the Servicemap system",
                        max_length=10,
                        null=True,
                        unique=True,
                        verbose_name="servicemap ID",
                    ),
                ),
                (
                    "zip_code",
                    models.CharField(max_length=10, verbose_name="postal code"),
                ),
                (
                    "phone",
                    models.CharField(
                        blank=True, max_length=30, verbose_name="phone number"
                    ),
                ),
                (
                    "email",
                    models.EmailField(blank=True, max_length=100, verbose_name="email"),
                ),
                (
                    "www_url",
                    models.URLField(
                        blank=True, max_length=400, verbose_name="WWW link"
                    ),
                ),
                (
                    "location",
                    django.contrib.gis.db.models.fields.PointField(
                        blank=True, null=True, srid=4326, verbose_name="location"
                    ),
                ),
                (
                    "image_link",
                    models.URLField(
                        blank=True, max_length=400, verbose_name="image link"
                    ),
                ),
                (
                    "image_file",
                    models.ImageField(
                        blank=True,
                        null=True,
                        storage=resources.models.OverwriteStorage(),
                        upload_to=resources.models.get_harbor_media_folder,
                        verbose_name="image file",
                    ),
                ),
                (
                    "number_of_places",
                    models.PositiveSmallIntegerField(
                        blank=True, null=True, verbose_name="number of places"
                    ),
                ),
                (
                    "maximum_width",
                    models.PositiveSmallIntegerField(
                        blank=True, null=True, verbose_name="maximum berth width"
                    ),
                ),
                (
                    "maximum_length",
                    models.PositiveSmallIntegerField(
                        blank=True, null=True, verbose_name="maximum berth length"
                    ),
                ),
                (
                    "maximum_depth",
                    models.PositiveSmallIntegerField(
                        blank=True, null=True, verbose_name="maximum berth depth"
                    ),
                ),
                (
                    "availability_level",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="harbors",
                        to="resources.AvailabilityLevel",
                        verbose_name="availability level",
                    ),
                ),
                (
                    "municipality",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="harbors",
                        to="munigeo.Municipality",
                        verbose_name="municipality",
                    ),
                ),
            ],
            options={"verbose_name": "harbor", "verbose_name_plural": "harbors"},
            bases=(parler.models.TranslatableModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="WinterStorageArea",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "servicemap_id",
                    models.CharField(
                        blank=True,
                        help_text="ID in the Servicemap system",
                        max_length=10,
                        null=True,
                        unique=True,
                        verbose_name="servicemap ID",
                    ),
                ),
                (
                    "zip_code",
                    models.CharField(max_length=10, verbose_name="postal code"),
                ),
                (
                    "phone",
                    models.CharField(
                        blank=True, max_length=30, verbose_name="phone number"
                    ),
                ),
                (
                    "email",
                    models.EmailField(blank=True, max_length=100, verbose_name="email"),
                ),
                (
                    "www_url",
                    models.URLField(
                        blank=True, max_length=400, verbose_name="WWW link"
                    ),
                ),
                (
                    "location",
                    django.contrib.gis.db.models.fields.PointField(
                        blank=True, null=True, srid=4326, verbose_name="location"
                    ),
                ),
                (
                    "image_link",
                    models.URLField(
                        blank=True, max_length=400, verbose_name="image link"
                    ),
                ),
                (
                    "image_file",
                    models.ImageField(
                        blank=True,
                        null=True,
                        storage=resources.models.OverwriteStorage(),
                        upload_to=resources.models.get_winter_area_media_folder,
                        verbose_name="image file",
                    ),
                ),
                (
                    "number_of_marked_places",
                    models.PositiveSmallIntegerField(
                        blank=True, null=True, verbose_name="number of marked places"
                    ),
                ),
                (
                    "max_width",
                    models.PositiveSmallIntegerField(
                        blank=True, null=True, verbose_name="maximum place width"
                    ),
                ),
                (
                    "max_length",
                    models.PositiveSmallIntegerField(
                        blank=True, null=True, verbose_name="maximum place length"
                    ),
                ),
                (
                    "number_of_section_spaces",
                    models.PositiveSmallIntegerField(
                        blank=True, null=True, verbose_name="number of section places"
                    ),
                ),
                (
                    "max_length_of_section_spaces",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        null=True,
                        verbose_name="xaximum length of section spaces",
                    ),
                ),
                (
                    "number_of_unmarked_spaces",
                    models.PositiveSmallIntegerField(
                        blank=True, null=True, verbose_name="number of unmarked places"
                    ),
                ),
                (
                    "availability_level",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="winter_storage_areas",
                        to="resources.AvailabilityLevel",
                        verbose_name="availability level",
                    ),
                ),
                (
                    "municipality",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="winter_storage_areas",
                        to="munigeo.Municipality",
                        verbose_name="municipality",
                    ),
                ),
            ],
            options={
                "verbose_name": "winter storage area",
                "verbose_name_plural": "winter storage areas",
            },
            bases=(parler.models.TranslatableModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="WinterStorageSection",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "identifier",
                    models.CharField(
                        blank=True,
                        help_text="Identifier of the pier / section",
                        max_length=30,
                        verbose_name="identifier",
                    ),
                ),
                (
                    "location",
                    django.contrib.gis.db.models.fields.PointField(
                        blank=True, null=True, srid=4326, verbose_name="location"
                    ),
                ),
                (
                    "electricity",
                    models.BooleanField(default=False, verbose_name="electricity"),
                ),
                ("water", models.BooleanField(default=False, verbose_name="water")),
                ("gate", models.BooleanField(default=False, verbose_name="gate")),
                (
                    "repair_area",
                    models.BooleanField(default=False, verbose_name="repair area"),
                ),
                (
                    "summer_storage_for_docking_equipment",
                    models.BooleanField(
                        default=False,
                        verbose_name="summer storage for docking equipment",
                    ),
                ),
                (
                    "summer_storage_for_trailers",
                    models.BooleanField(
                        default=False, verbose_name="summer storage for trailers"
                    ),
                ),
                (
                    "summer_storage_for_boats",
                    models.BooleanField(
                        default=False, verbose_name="summer storage for boats"
                    ),
                ),
                (
                    "area",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sections",
                        to="resources.WinterStorageArea",
                        verbose_name="winter storage area",
                    ),
                ),
            ],
            options={
                "verbose_name": "winter storage section",
                "verbose_name_plural": "winter storage sections",
                "ordering": ("area", "identifier"),
                "unique_together": {("area", "identifier")},
            },
        ),
        migrations.CreateModel(
            name="WinterStoragePlaceType",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("width", models.PositiveSmallIntegerField(verbose_name="width (cm)")),
                (
                    "length",
                    models.PositiveSmallIntegerField(verbose_name="length (cm)"),
                ),
            ],
            options={
                "verbose_name": "winter storage place type",
                "verbose_name_plural": "winter storage place types",
                "ordering": ("width", "length"),
                "unique_together": {("width", "length")},
            },
        ),
        migrations.CreateModel(
            name="Pier",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "identifier",
                    models.CharField(
                        blank=True,
                        help_text="Identifier of the pier / section",
                        max_length=30,
                        verbose_name="identifier",
                    ),
                ),
                (
                    "location",
                    django.contrib.gis.db.models.fields.PointField(
                        blank=True, null=True, srid=4326, verbose_name="location"
                    ),
                ),
                (
                    "electricity",
                    models.BooleanField(default=False, verbose_name="electricity"),
                ),
                ("water", models.BooleanField(default=False, verbose_name="water")),
                ("gate", models.BooleanField(default=False, verbose_name="gate")),
                ("mooring", models.BooleanField(default=False, verbose_name="mooring")),
                (
                    "waste_collection",
                    models.BooleanField(default=False, verbose_name="waste collection"),
                ),
                (
                    "lighting",
                    models.BooleanField(default=False, verbose_name="lighting"),
                ),
                (
                    "harbor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="piers",
                        to="resources.Harbor",
                        verbose_name="harbor",
                    ),
                ),
                (
                    "suitable_boat_types",
                    models.ManyToManyField(
                        blank=True,
                        related_name="piers",
                        to="resources.BoatType",
                        verbose_name="suitable boat types",
                    ),
                ),
            ],
            options={
                "verbose_name": "pier",
                "verbose_name_plural": "piers",
                "ordering": ("harbor", "identifier"),
                "unique_together": {("identifier", "harbor")},
            },
        ),
        migrations.CreateModel(
            name="BerthType",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("width", models.PositiveSmallIntegerField(verbose_name="width (cm)")),
                (
                    "length",
                    models.PositiveSmallIntegerField(verbose_name="length (cm)"),
                ),
                (
                    "mooring_type",
                    enumfields.fields.EnumIntegerField(
                        enum=resources.enums.BerthMooringType,
                        verbose_name="mooring type",
                    ),
                ),
            ],
            options={
                "verbose_name": "berth type",
                "verbose_name_plural": "berth types",
                "ordering": ("width", "length"),
                "unique_together": {("width", "length", "mooring_type")},
            },
        ),
        migrations.CreateModel(
            name="WinterStoragePlace",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("number", models.CharField(max_length=10, verbose_name="number")),
                (
                    "place_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="places",
                        to="resources.WinterStoragePlaceType",
                        verbose_name="place type",
                    ),
                ),
                (
                    "winter_storage_section",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="places",
                        to="resources.WinterStorageSection",
                        verbose_name="winter storage section",
                    ),
                ),
            ],
            options={
                "verbose_name": "winter storage place",
                "verbose_name_plural": "winter storage places",
                "ordering": ("winter_storage_section", "number"),
                "unique_together": {("winter_storage_section", "number")},
            },
        ),
        migrations.CreateModel(
            name="WinterStorageAreaTranslation",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "language_code",
                    models.CharField(
                        db_index=True, max_length=15, verbose_name="Language"
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        blank=True,
                        help_text="Name of the area",
                        max_length=200,
                        verbose_name="name",
                    ),
                ),
                (
                    "street_address",
                    models.CharField(
                        blank=True,
                        help_text="Street address of the area",
                        max_length=200,
                        verbose_name="street address",
                    ),
                ),
                (
                    "master",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="translations",
                        to="resources.WinterStorageArea",
                    ),
                ),
            ],
            options={
                "verbose_name": "winter storage area Translation",
                "db_table": "resources_winterstoragearea_translation",
                "db_tablespace": "",
                "managed": True,
                "default_permissions": (),
                "unique_together": {("language_code", "master")},
            },
        ),
        migrations.CreateModel(
            name="HarborTranslation",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "language_code",
                    models.CharField(
                        db_index=True, max_length=15, verbose_name="Language"
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        blank=True,
                        help_text="Name of the harbor",
                        max_length=200,
                        verbose_name="name",
                    ),
                ),
                (
                    "street_address",
                    models.CharField(
                        blank=True,
                        help_text="Street address of the harbor",
                        max_length=200,
                        verbose_name="street address",
                    ),
                ),
                (
                    "master",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="translations",
                        to="resources.Harbor",
                    ),
                ),
            ],
            options={
                "verbose_name": "harbor Translation",
                "db_table": "resources_harbor_translation",
                "db_tablespace": "",
                "managed": True,
                "default_permissions": (),
                "unique_together": {("language_code", "master")},
            },
        ),
        migrations.CreateModel(
            name="BoatTypeTranslation",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "language_code",
                    models.CharField(
                        db_index=True, max_length=15, verbose_name="Language"
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Name of the boat type",
                        max_length=200,
                        verbose_name="name",
                    ),
                ),
                (
                    "master",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="translations",
                        to="resources.BoatType",
                    ),
                ),
            ],
            options={
                "verbose_name": "boat type Translation",
                "db_table": "resources_boattype_translation",
                "db_tablespace": "",
                "managed": True,
                "default_permissions": (),
                "unique_together": {("language_code", "master")},
            },
        ),
        migrations.CreateModel(
            name="Berth",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("number", models.CharField(max_length=10, verbose_name="number")),
                (
                    "berth_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="berths",
                        to="resources.BerthType",
                        verbose_name="berth type",
                    ),
                ),
                (
                    "pier",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="berths",
                        to="resources.Pier",
                        verbose_name="pier",
                    ),
                ),
            ],
            options={
                "verbose_name": "berth",
                "verbose_name_plural": "berths",
                "ordering": ("pier", "number"),
                "unique_together": {("pier", "number")},
            },
        ),
        migrations.CreateModel(
            name="AvailabilityLevelTranslation",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "language_code",
                    models.CharField(
                        db_index=True, max_length=15, verbose_name="Language"
                    ),
                ),
                (
                    "title",
                    models.CharField(
                        blank=True,
                        help_text="Title of the availability level",
                        max_length=64,
                        verbose_name="title",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Description of the availability level",
                        max_length=200,
                        verbose_name="description",
                    ),
                ),
                (
                    "master",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="translations",
                        to="resources.AvailabilityLevel",
                    ),
                ),
            ],
            options={
                "verbose_name": "availability level Translation",
                "db_table": "resources_availabilitylevel_translation",
                "db_tablespace": "",
                "managed": True,
                "default_permissions": (),
                "unique_together": {("language_code", "master")},
            },
        ),
    ]
