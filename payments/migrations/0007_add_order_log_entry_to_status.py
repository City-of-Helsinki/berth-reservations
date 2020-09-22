# Generated by Django 3.1 on 2020-08-19 09:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0006_add_cancelled_order_status"),
    ]

    operations = [
        migrations.RenameField(
            model_name="orderlogentry", old_name="status", new_name="to_status",
        ),
        migrations.AddField(
            model_name="orderlogentry",
            name="from_status",
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
            preserve_default=False,
        ),
    ]