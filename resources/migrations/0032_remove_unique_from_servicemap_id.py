# Generated by Django 3.1 on 2021-05-21 10:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0031_remove_area_map_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="harbor",
            name="servicemap_id",
            field=models.CharField(
                blank=True,
                help_text="ID in the Servicemap system",
                max_length=10,
                null=True,
                verbose_name="servicemap ID",
            ),
        ),
        migrations.AlterField(
            model_name="winterstoragearea",
            name="servicemap_id",
            field=models.CharField(
                blank=True,
                help_text="ID in the Servicemap system",
                max_length=10,
                null=True,
                verbose_name="servicemap ID",
            ),
        ),
    ]
