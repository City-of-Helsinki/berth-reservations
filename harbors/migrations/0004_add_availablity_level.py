# Generated by Django 2.1.2 on 2018-12-20 10:02

from django.db import migrations, models
import django.db.models.deletion
import parler.models


class Migration(migrations.Migration):

    dependencies = [("harbors", "0003_add_overwrite_storage")]

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
                ),
                (
                    "identifier",
                    models.CharField(
                        max_length=100, unique=True, verbose_name="Unique identifier"
                    ),
                ),
            ],
            options={
                "verbose_name": "availability level",
                "verbose_name_plural": "availability levels",
                "ordering": ("id",),
            },
            bases=(parler.models.TranslatableModelMixin, models.Model),
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
                    "description",
                    models.TextField(
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
                        to="harbors.AvailabilityLevel",
                    ),
                ),
            ],
            options={
                "verbose_name": "availability level Translation",
                "db_table": "harbors_availabilitylevel_translation",
                "db_tablespace": "",
                "managed": True,
                "default_permissions": (),
            },
        ),
        migrations.AlterField(
            model_name="harbor",
            name="municipality",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="harbors",
                to="munigeo.Municipality",
                verbose_name="Municipality",
            ),
        ),
        migrations.AddField(
            model_name="harbor",
            name="availability_level",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="harbors",
                to="harbors.AvailabilityLevel",
                verbose_name="Availability level",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="availabilityleveltranslation",
            unique_together={("language_code", "master")},
        ),
    ]