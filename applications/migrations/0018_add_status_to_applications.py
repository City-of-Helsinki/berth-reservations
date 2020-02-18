# Generated by Django 2.2.6 on 2020-02-07 11:40

import applications.enums
from django.db import migrations
import enumfields.fields


class Migration(migrations.Migration):

    dependencies = [
        ("applications", "0017_add_customer_to_berth_application"),
    ]

    operations = [
        migrations.AddField(
            model_name="berthapplication",
            name="status",
            field=enumfields.fields.EnumField(
                default="pending",
                enum=applications.enums.ApplicationStatus,
                max_length=32,
                verbose_name="handling status",
            ),
        ),
        migrations.AddField(
            model_name="winterstorageapplication",
            name="status",
            field=enumfields.fields.EnumField(
                default="pending",
                enum=applications.enums.ApplicationStatus,
                max_length=32,
                verbose_name="handling status",
            ),
        ),
    ]