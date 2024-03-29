# Generated by Django 3.1.7 on 2021-08-18 10:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("leases", "0014_remove_renew_automatically"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="berthlease",
            options={
                "default_related_name": "berth_leases",
                "ordering": ("-start_date", "-end_date", "created_at"),
                "verbose_name": "berth lease",
                "verbose_name_plural": "berth leases",
            },
        ),
        migrations.AlterModelOptions(
            name="winterstoragelease",
            options={
                "default_related_name": "winter_storage_leases",
                "ordering": ("-start_date", "-end_date", "created_at"),
                "verbose_name": "winter storage lease",
                "verbose_name_plural": "winter storage leases",
            },
        ),
    ]
