# Generated by Django 3.1 on 2021-03-19 08:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0025_add_berth_switch_offer_logs"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="berthswitchofferlogentry",
            options={"verbose_name_plural": "berth switch offer log entries"},
        ),
        migrations.AlterField(
            model_name="berthswitchoffer",
            name="due_date",
            field=models.DateField(null=True, blank=True, verbose_name="due date"),
        ),
        migrations.AlterField(
            model_name="berthswitchoffer",
            name="status",
            field=models.CharField(
                choices=[
                    ("drafted", "Drafted"),
                    ("offered", "Offered"),
                    ("accepted", "Accepted"),
                    ("rejected", "Rejected"),
                    ("expired", "Expired"),
                    ("cancelled", "Cancelled"),
                ],
                default="drafted",
                max_length=9,
            ),
        ),
        migrations.AlterField(
            model_name="berthswitchofferlogentry",
            name="from_status",
            field=models.CharField(
                choices=[
                    ("drafted", "Drafted"),
                    ("offered", "Offered"),
                    ("accepted", "Accepted"),
                    ("rejected", "Rejected"),
                    ("expired", "Expired"),
                    ("cancelled", "Cancelled"),
                ],
                max_length=9,
            ),
        ),
        migrations.AlterField(
            model_name="berthswitchofferlogentry",
            name="to_status",
            field=models.CharField(
                choices=[
                    ("drafted", "Drafted"),
                    ("offered", "Offered"),
                    ("accepted", "Accepted"),
                    ("rejected", "Rejected"),
                    ("expired", "Expired"),
                    ("cancelled", "Cancelled"),
                ],
                max_length=9,
            ),
        ),
    ]
