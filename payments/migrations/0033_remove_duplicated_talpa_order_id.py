# Generated by Django 3.2.8 on 2021-11-23 13:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0032_remove_talpa_accounting_id"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="order",
            name="talpa_order_id",
        ),
    ]