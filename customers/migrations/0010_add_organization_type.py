# Generated by Django 2.2.6 on 2020-04-15 14:34

import enumfields.fields
from django.db import migrations

import customers.enums


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0009_rename_company_to_organization"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="organization_type",
            field=enumfields.fields.EnumField(
                default="company",
                enum=customers.enums.OrganizationType,
                max_length=16,
                verbose_name="organization type",
            ),
            preserve_default=False,
        ),
    ]