# Generated by Django 2.2.6 on 2020-05-12 13:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0014_change_place_number_to_integer"),
    ]

    operations = [
        migrations.AlterUniqueTogether(name="berthtype", unique_together=set(),),
        migrations.AddConstraint(
            model_name="berthtype",
            constraint=models.UniqueConstraint(
                fields=("width", "length", "depth", "mooring_type"),
                name="unique_dimension",
            ),
        ),
    ]