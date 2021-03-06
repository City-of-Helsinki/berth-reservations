# Generated by Django 2.2.6 on 2020-07-16 09:39

from django.db import migrations, models
import leases.utils


class Migration(migrations.Migration):

    dependencies = [
        ("leases", "0006_add_renew_automatically_to_berth_leases"),
    ]

    operations = [
        migrations.AlterField(
            model_name="winterstoragelease",
            name="end_date",
            field=models.DateField(
                default=leases.utils.calculate_winter_storage_lease_end_date,
                verbose_name="end date",
            ),
        ),
        migrations.AlterField(
            model_name="winterstoragelease",
            name="start_date",
            field=models.DateField(
                default=leases.utils.calculate_winter_storage_lease_start_date,
                verbose_name="start date",
            ),
        ),
    ]
