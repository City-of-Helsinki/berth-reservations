# Generated by Django 2.2.6 on 2020-02-07 11:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("applications", "0017_add_customer_to_berth_application"),
    ]

    operations = [
        migrations.AddField(
            model_name="berthapplication",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("offer_generated", "Offer generated"),
                    ("offer_sent", "Offer sent"),
                    ("no_suitable_berths", "No suitable berths"),
                    (
                        "no_suitable_berths_notified",
                        "Notified that there are no suitable berths",
                    ),
                    ("handled", "Handled"),
                    ("expired", "Expired"),
                ],
                default="pending",
                max_length=32,
                verbose_name="handling status",
            ),
        ),
        migrations.AddField(
            model_name="winterstorageapplication",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("offer_generated", "Offer generated"),
                    ("offer_sent", "Offer sent"),
                    ("no_suitable_berths", "No suitable berths"),
                    (
                        "no_suitable_berths_notified",
                        "Notified that there are no suitable berths",
                    ),
                    ("handled", "Handled"),
                    ("expired", "Expired"),
                ],
                default="pending",
                max_length=32,
                verbose_name="handling status",
            ),
        ),
    ]
