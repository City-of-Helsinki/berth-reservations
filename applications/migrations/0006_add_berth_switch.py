# Generated by Django 2.1.2 on 2019-04-08 11:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("applications", "0005_add_custom_permissions"),
    ]

    operations = [
        migrations.CreateModel(
            name="BerthSwitch",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "pier",
                    models.CharField(blank=True, max_length=40, verbose_name="pier"),
                ),
                (
                    "berth_number",
                    models.CharField(max_length=20, verbose_name="berth number"),
                ),
                (
                    "harbor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="resources.Harbor",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="reservation",
            name="berth_switch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="applications.BerthSwitch",
                verbose_name="berth switch",
            ),
        ),
    ]
