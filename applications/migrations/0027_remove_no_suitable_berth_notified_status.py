# Generated by Django 3.1 on 2021-03-01 12:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("applications", "0026_add_rejected_application_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="berthapplication",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("offer_generated", "Offer generated"),
                    ("offer_sent", "Offer sent"),
                    ("no_suitable_berths", "No suitable berths"),
                    ("handled", "Handled"),
                    ("rejected", "Rejected"),
                    ("expired", "Expired"),
                ],
                default="pending",
                max_length=32,
                verbose_name="handling status",
            ),
        ),
        migrations.AlterField(
            model_name="winterstorageapplication",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("offer_generated", "Offer generated"),
                    ("offer_sent", "Offer sent"),
                    ("no_suitable_berths", "No suitable berths"),
                    ("handled", "Handled"),
                    ("rejected", "Rejected"),
                    ("expired", "Expired"),
                ],
                default="pending",
                max_length=32,
                verbose_name="handling status",
            ),
        ),
    ]
