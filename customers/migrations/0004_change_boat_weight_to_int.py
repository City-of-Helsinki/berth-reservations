# Generated by Django 2.2.6 on 2020-01-09 13:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0003_add_validators_to_boat_dimensions"),
    ]

    operations = [
        migrations.AlterField(
            model_name="boat",
            name="weight",
            field=models.PositiveIntegerField(
                blank=True, null=True, verbose_name="weight (kg)"
            ),
        ),
    ]
