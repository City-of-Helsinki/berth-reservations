# Generated by Django 2.2.6 on 2020-04-22 12:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0010_add_organization_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="boat",
            name="intended_use",
            field=models.TextField(blank=True, verbose_name="intended use"),
        ),
    ]
