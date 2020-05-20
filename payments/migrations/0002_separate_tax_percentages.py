# Generated by Django 2.2.6 on 2020-05-19 07:58

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="berthproduct",
            name="tax_percentage",
            field=models.DecimalField(
                choices=[(Decimal("24.00"), "24.00")],
                decimal_places=2,
                default=Decimal("24.0"),
                max_digits=5,
                verbose_name="tax percentage",
            ),
        ),
        migrations.AlterField(
            model_name="winterstorageproduct",
            name="tax_percentage",
            field=models.DecimalField(
                choices=[(Decimal("24.00"), "24.00")],
                decimal_places=2,
                default=Decimal("24.0"),
                max_digits=5,
                verbose_name="tax percentage",
            ),
        ),
    ]