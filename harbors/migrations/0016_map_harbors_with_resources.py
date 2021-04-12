# Generated by Django 3.1 on 2021-03-16 13:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0026_berth_is_invoiceable"),
        ("harbors", "0015_change_image_file_to_char"),
    ]

    operations = [
        migrations.AddField(
            model_name="harbor",
            name="resources_harbor",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="harbors_harbor",
                to="resources.harbor",
            ),
        ),
    ]