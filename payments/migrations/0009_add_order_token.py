# Generated by Django 3.1 on 2020-10-02 11:38

from decimal import Decimal
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0008_update_price_validator"),
    ]

    operations = [
        migrations.CreateModel(
            name="OrderToken",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="time created"
                    ),
                ),
                (
                    "modified_at",
                    models.DateTimeField(auto_now=True, verbose_name="time modified"),
                ),
                (
                    "token",
                    models.CharField(
                        max_length=64, verbose_name="token", blank=True, null=True
                    ),
                ),
                ("valid_until", models.DateTimeField(verbose_name="valid until")),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tokens",
                        to="payments.order",
                        verbose_name="order tokens",
                    ),
                ),
            ],
            options={"abstract": False},
        ),
    ]