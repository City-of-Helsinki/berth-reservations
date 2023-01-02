# Generated by Django 3.1 on 2021-03-16 13:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0026_berth_is_invoiceable"),
    ]

    operations = [
        migrations.AddField(
            model_name="pier",
            name="harbors_harbor",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="resources_pier",
                to="resources.harbor",
            ),
        ),
    ]