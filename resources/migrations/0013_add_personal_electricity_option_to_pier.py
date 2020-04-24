# Generated by Django 2.2.6 on 2020-04-16 09:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0012_add_is_active_to_boat_places"),
    ]

    operations = [
        migrations.AddField(
            model_name="pier",
            name="personal_electricity",
            field=models.BooleanField(
                default=False, verbose_name="personal electricity contract"
            ),
        ),
    ]