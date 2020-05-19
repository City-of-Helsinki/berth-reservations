from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.utils.translation import ugettext_lazy as _
from enumfields import EnumField

from payments.enums import AdditionalProductType, PeriodType, PriceUnits, ServiceType
from utils.models import TimeStampedModel, UUIDModel

PLACE_PRODUCT_TAX_PERCENTAGES = [Decimal(x) for x in ("24.00",)]
ADDITIONAL_PRODUCT_TAX_PERCENTAGES = [Decimal(x) for x in ("24.00", "10.00")]

DEFAULT_TAX_PERCENTAGE = Decimal("24.0")


class AbstractBaseProduct(TimeStampedModel, UUIDModel):
    price_value = models.DecimalField(
        verbose_name=_("price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    price_unit = EnumField(PriceUnits, default=PriceUnits.AMOUNT)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class BerthPriceGroupManager(models.Manager):
    def get_or_create_for_width(self, width):
        # One single common way to get a BPG based on the width
        return self.get_or_create(name=f"{width}m")


class BerthPriceGroup(UUIDModel):
    name = models.CharField(
        verbose_name=_("berth price group name"), max_length=128, unique=True
    )
    objects = BerthPriceGroupManager()

    def __str__(self):
        return f"{self.name} ({self.id})"


class AbstractPlaceProduct(AbstractBaseProduct):
    price_unit = EnumField(
        PriceUnits,
        choices=[(PriceUnits.AMOUNT, PriceUnits.AMOUNT.label)],
        default=PriceUnits.AMOUNT,
    )
    tax_percentage = models.DecimalField(
        verbose_name=_("tax percentage"),
        max_digits=5,
        decimal_places=2,
        default=DEFAULT_TAX_PERCENTAGE,
        choices=[(tax, str(tax)) for tax in PLACE_PRODUCT_TAX_PERCENTAGES],
    )

    class Meta:
        abstract = True


class BerthProduct(AbstractPlaceProduct):
    price_group = models.ForeignKey(
        BerthPriceGroup,
        on_delete=models.CASCADE,
        verbose_name=_("price group"),
        related_name="products",
    )
    harbor = models.ForeignKey(
        "resources.Harbor",
        verbose_name=_("harbor"),
        related_name="products",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["price_group", "harbor"],
                name="unique_product_for_harbor_pricegroup",
            ),
        ]

    def __str__(self):
        return f"{self.price_group} - {self.harbor} ({self.price_value}€)"


class WinterStorageProduct(AbstractPlaceProduct):
    winter_storage_area = models.OneToOneField(
        "resources.WinterStorageArea",
        verbose_name=_("winter storage area"),
        related_name="product",
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return f"{self.winter_storage_area} ({self.price_value}€)"


class AdditionalProduct(AbstractBaseProduct):
    service = EnumField(ServiceType, verbose_name=_("service"), max_length=40)
    period = EnumField(PeriodType, max_length=8)
    tax_percentage = models.DecimalField(
        verbose_name=_("tax percentage"),
        max_digits=5,
        decimal_places=2,
        default=DEFAULT_TAX_PERCENTAGE,
        choices=[(tax, str(tax)) for tax in ADDITIONAL_PRODUCT_TAX_PERCENTAGES],
    )

    @property
    def product_type(self):
        if self.service.is_fixed_service():
            return AdditionalProductType.FIXED_SERVICE
        elif self.service.is_optional_service():
            return AdditionalProductType.OPTIONAL_SERVICE
        return None

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["service", "period"],
                condition=Q(service__in=ServiceType.OPTIONAL_SERVICES()),
                name="optional_services_per_period",
            ),
        ]

    def clean(self):
        if self.service.is_fixed_service():
            if self.tax_percentage != DEFAULT_TAX_PERCENTAGE:
                raise ValidationError(
                    _(f"Fixed services must have VAT of {DEFAULT_TAX_PERCENTAGE}€")
                )
            if self.period != PeriodType.SEASON:
                raise ValidationError(_(f"Fixed services are only valid for season"))

    def __str__(self):
        return (
            f"{self.service} - {self.period} "
            f"({self.price_value}{'€' if self.price_unit == PriceUnits.AMOUNT else '%'})"
        )
