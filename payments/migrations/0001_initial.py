# Generated by Django 2.2.6 on 2020-05-15 06:38

from decimal import Decimal
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import payments.enums
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("resources", "0015_add_depth_to_berthtype_unique"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdditionalProduct",
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
                    "price_value",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=10,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.01"))
                        ],
                        verbose_name="price",
                    ),
                ),
                (
                    "price_unit",
                    models.CharField(
                        choices=[("amount", "Amount"), ("percentage", "Percentage")],
                        default="amount",
                        max_length=10,
                    ),
                ),
                (
                    "tax_percentage",
                    models.DecimalField(
                        choices=[
                            (Decimal("24.00"), "24.00"),
                            (Decimal("10.00"), "10.00"),
                        ],
                        decimal_places=2,
                        default=Decimal("24.0"),
                        max_digits=5,
                        verbose_name="tax percentage",
                    ),
                ),
                (
                    "service",
                    models.CharField(
                        choices=[
                            ("electricity", "Electricity"),
                            ("water", "Water"),
                            ("gate", "Gate"),
                            ("mooring", "Mooring"),
                            ("waste_collection", "Waste collection"),
                            ("lighting", "Lighting"),
                            (
                                "summer_storage_for_docking_equipment",
                                "Summer storage for docking equipment",
                            ),
                            (
                                "summer_storage_for_trailers",
                                "Summer storage for trailers",
                            ),
                            ("parking_permit", "Parking permit"),
                            ("dinghy_place", "Dinghy place"),
                        ],
                        max_length=40,
                        verbose_name="service",
                    ),
                ),
                (
                    "period",
                    models.CharField(
                        choices=[
                            ("year", "Year"),
                            ("season", "Season"),
                            ("month", "Month"),
                        ],
                        max_length=8,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="BerthPriceGroup",
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
                    "name",
                    models.CharField(
                        max_length=128,
                        verbose_name="berth price group name",
                        unique=True,
                    ),
                ),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="WinterStorageProduct",
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
                    "price_value",
                    models.DecimalField(
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
                        choices=[(Decimal("24.0"), "24.0")],
                        decimal_places=2,
                        default=Decimal("24.0"),
                        max_digits=5,
                        verbose_name="tax percentage",
                    ),
                ),
                (
                    "price_unit",
                    models.CharField(
                        choices=[("amount", "Amount")],
                        default="amount",
                        max_length=10,
                    ),
                ),
                (
                    "winter_storage_area",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="product",
                        to="resources.WinterStorageArea",
                        verbose_name="winter storage area",
                    ),
                ),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="BerthProduct",
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
                    "price_value",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=10,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.01"))
                        ],
                        verbose_name="price",
                    ),
                ),
                (
                    "price_unit",
                    models.CharField(
                        choices=[("amount", "Amount")],
                        default="amount",
                        max_length=10,
                    ),
                ),
                (
                    "tax_percentage",
                    models.DecimalField(
                        choices=[(Decimal("24.0"), "24.0")],
                        decimal_places=2,
                        default=Decimal("24.0"),
                        max_digits=5,
                        verbose_name="tax percentage",
                    ),
                ),
                (
                    "harbor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="products",
                        to="resources.Harbor",
                        verbose_name="harbor",
                    ),
                ),
                (
                    "price_group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="products",
                        to="payments.BerthPriceGroup",
                        verbose_name="price group",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="additionalproduct",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    service__in=[
                        payments.enums.ProductServiceType(
                            "summer_storage_for_docking_equipment"
                        ),
                        payments.enums.ProductServiceType(
                            "summer_storage_for_trailers"
                        ),
                        payments.enums.ProductServiceType("parking_permit"),
                        payments.enums.ProductServiceType("dinghy_place"),
                    ]
                ),
                fields=("service", "period"),
                name="optional_services_per_period",
            ),
        ),
        migrations.AddConstraint(
            model_name="berthproduct",
            constraint=models.UniqueConstraint(
                fields=("price_group", "harbor"),
                name="unique_product_for_harbor_pricegroup",
            ),
        ),
    ]
