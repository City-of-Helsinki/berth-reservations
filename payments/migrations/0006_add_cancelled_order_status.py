# Generated by Django 3.1 on 2020-08-19 08:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0005_add_order_number"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("waiting", "Waiting"),
                    ("rejected", "Rejected"),
                    ("cancelled", "Cancelled"),
                    ("expired", "Expired"),
                    ("paid", "Paid"),
                ],
                default="waiting",
                max_length=9,
            ),
        ),
        migrations.AlterField(
            model_name="orderlogentry",
            name="status",
            field=models.CharField(
                choices=[
                    ("waiting", "Waiting"),
                    ("rejected", "Rejected"),
                    ("cancelled", "Cancelled"),
                    ("expired", "Expired"),
                    ("paid", "Paid"),
                ],
                max_length=9,
            ),
        ),
    ]