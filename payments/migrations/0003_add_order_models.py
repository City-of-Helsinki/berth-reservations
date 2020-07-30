# Generated by Django 2.2.6 on 2020-06-10 12:44

from decimal import Decimal
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import payments.utils
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("customers", "0012_add_boat_certificates"),
        ("payments", "0002_separate_tax_percentages"),
    ]

    operations = [
        migrations.CreateModel(
            name="Order",
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
                    "status",
                    models.CharField(
                        choices=[
                            ("waiting", "Waiting"),
                            ("rejected", "Rejected"),
                            ("expired", "Expired"),
                            ("paid", "Paid"),
                        ],
                        default="waiting",
                        max_length=8,
                    ),
                ),
                ("comment", models.TextField(blank=True, null=True)),
                (
                    "price",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=10,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.01"))
                        ],
                        verbose_name="price",
                    ),
                ),
                (
                    "tax_percentage",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=5,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.00"))
                        ],
                        verbose_name="tax percentage",
                    ),
                ),
                (
                    "due_date",
                    models.DateField(
                        default=payments.utils.calculate_order_due_date,
                        verbose_name="due date",
                    ),
                ),
                (
                    "_product_object_id",
                    models.UUIDField(blank=True, null=True, verbose_name="product"),
                ),
                (
                    "_lease_object_id",
                    models.UUIDField(blank=True, null=True, verbose_name="lease"),
                ),
                (
                    "_lease_content_type",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="lease",
                        to="contenttypes.ContentType",
                    ),
                ),
                (
                    "_product_content_type",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="product",
                        to="contenttypes.ContentType",
                    ),
                ),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="orders",
                        to="customers.CustomerProfile",
                        verbose_name="customer",
                    ),
                ),
            ],
            options={"abstract": False,},
        ),
        migrations.CreateModel(
            name="OrderLogEntry",
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
                    "status",
                    models.CharField(
                        choices=[
                            ("waiting", "Waiting"),
                            ("rejected", "Rejected"),
                            ("expired", "Expired"),
                            ("paid", "Paid"),
                        ],
                        max_length=8,
                    ),
                ),
                ("comment", models.TextField(blank=True, null=True)),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="log_entries",
                        to="payments.Order",
                        verbose_name="order log entry",
                    ),
                ),
            ],
            options={"verbose_name_plural": "order log entries",},
        ),
        migrations.CreateModel(
            name="OrderLine",
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
                    "quantity",
                    models.PositiveSmallIntegerField(
                        default=1,
                        validators=[django.core.validators.MinValueValidator(1)],
                        verbose_name="quantity",
                    ),
                ),
                (
                    "price",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=10,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.01"))
                        ],
                        verbose_name="price",
                    ),
                ),
                (
                    "tax_percentage",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=5,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.00"))
                        ],
                        verbose_name="tax percentage",
                    ),
                ),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="order_lines",
                        to="payments.Order",
                        verbose_name="order",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="orders_lines",
                        to="payments.AdditionalProduct",
                        verbose_name="product",
                    ),
                ),
            ],
            options={"abstract": False,},
        ),
    ]
