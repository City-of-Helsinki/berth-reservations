# Generated by Django 3.1 on 2020-09-21 11:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0013_rename_boat_media_directory_function"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organization",
            name="postal_code",
            field=models.CharField(
                blank=True, max_length=10, verbose_name="postal code"
            ),
        ),
    ]