# Generated by Django 3.1.7 on 2021-11-08 05:33

from decimal import Decimal
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0015_add_customer_user_relatedname"),
        ("applications", "0036_add_application_change_list"),
    ]

    operations = [
        migrations.AddField(
            model_name="berthapplication",
            name="boat",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="customers.boat",
                verbose_name="boat",
            ),
        ),
        migrations.AddField(
            model_name="winterstorageapplication",
            name="boat",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="customers.boat",
                verbose_name="boat",
            ),
        ),
        migrations.AlterField(
            model_name="berthapplication",
            name="boat_length",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=5,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
                verbose_name="boat length",
            ),
        ),
        migrations.AlterField(
            model_name="berthapplication",
            name="boat_width",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=5,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
                verbose_name="boat width",
            ),
        ),
        migrations.AlterField(
            model_name="winterstorageapplication",
            name="area_type",
            field=models.CharField(
                blank=True,
                choices=[("marked", "Marked"), ("unmarked", "Unmarked")],
                max_length=30,
                null=True,
                verbose_name="application area type",
            ),
        ),
        migrations.AlterField(
            model_name="winterstorageapplication",
            name="boat_length",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=5,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
                verbose_name="boat length",
            ),
        ),
        migrations.AlterField(
            model_name="winterstorageapplication",
            name="boat_width",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=5,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
                verbose_name="boat width",
            ),
        ),
    ]
