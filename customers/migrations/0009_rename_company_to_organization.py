# Generated by Django 2.2.6 on 2020-04-15 12:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0008_add_default_invoicing_type"),
    ]

    operations = [
        migrations.RenameModel("Company", "Organization"),
        migrations.AlterField(
            model_name="organization",
            name="business_id",
            field=models.CharField(
                blank=True, max_length=32, verbose_name="business id"
            ),
        ),
        migrations.AlterField(
            model_name="organization",
            name="customer",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="organization",
                to="customers.CustomerProfile",
                verbose_name="customer",
            ),
        ),
        migrations.AlterModelOptions(
            name="organization",
            options={
                "ordering": ("id",),
                "verbose_name": "organization",
                "verbose_name_plural": "organizations",
            },
        ),
    ]
