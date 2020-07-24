from decimal import Decimal

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.utils.translation import ugettext_lazy as _
from enumfields import EnumField

from leases.models import BerthLease, WinterStorageLease
from payments.enums import (
    AdditionalProductType,
    OrderStatus,
    PeriodType,
    PriceUnits,
    ProductServiceType,
)
from payments.utils import (
    calculate_order_due_date,
    calculate_product_partial_month_price,
    calculate_product_partial_season_price,
    calculate_product_partial_year_price,
    calculate_product_percentage_price,
    convert_aftertax_to_pretax,
    rounded,
)
from utils.models import TimeStampedModel, UUIDModel
from utils.numbers import rounded as rounded_decimal

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
    service = EnumField(ProductServiceType, verbose_name=_("service"), max_length=40)
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
                condition=Q(service__in=ProductServiceType.OPTIONAL_SERVICES()),
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


class OrderManager(models.Manager):
    def berth_orders(self):
        return self.get_queryset().filter(
            Q(
                Q(_product_content_type__model=BerthProduct._meta.model_name)
                | Q(_lease_content_type__model=BerthLease._meta.model_name)
            )
        )

    def winter_storage_orders(self):
        return self.get_queryset().filter(
            Q(
                Q(_product_content_type__model=WinterStorageProduct._meta.model_name)
                | Q(_lease_content_type__model=WinterStorageLease._meta.model_name)
            )
        )


class Order(UUIDModel, TimeStampedModel):
    customer = models.ForeignKey(
        "customers.CustomerProfile",
        verbose_name=_("customer"),
        on_delete=models.CASCADE,
        related_name="orders",
    )
    product = GenericForeignKey("_product_content_type", "_product_object_id")
    lease = GenericForeignKey("_lease_content_type", "_lease_object_id")
    status = EnumField(OrderStatus, default=OrderStatus.WAITING)
    comment = models.TextField(blank=True, null=True)
    price = models.DecimalField(
        verbose_name=_("price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        blank=True,
    )
    tax_percentage = models.DecimalField(
        verbose_name=_("tax percentage"),
        max_digits=5,
        decimal_places=2,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    due_date = models.DateField(
        verbose_name=_("due date"), default=calculate_order_due_date,
    )

    _product_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product",
    )
    _product_object_id = models.UUIDField(
        null=True, blank=True, verbose_name=_("product")
    )

    _lease_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lease",
    )
    _lease_object_id = models.UUIDField(null=True, blank=True, verbose_name=_("lease"))

    objects = OrderManager()

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["_lease_content_type", "_lease_object_id"], name="unique_lease"
            )
        ]

    def __str__(self):
        return f"{self.product} [{self.status}]"

    @property
    @rounded
    def pretax_price(self):
        return convert_aftertax_to_pretax(self.price, self.tax_percentage)

    @property
    @rounded
    def total_price(self):
        return sum([ol.price for ol in self.order_lines.all()], self.price)

    @property
    @rounded
    def total_pretax_price(self):
        return sum(
            [ol.pretax_price for ol in self.order_lines.all()], self.pretax_price
        )

    @property
    def total_tax_percentage(self):
        return rounded_decimal(
            ((self.total_price - self.total_pretax_price) / self.total_pretax_price)
            * 100,
            round_to_nearest=0.05,
        )

    def _check_valid_products(self) -> None:
        if self.product and not isinstance(
            self.product, (BerthProduct, WinterStorageProduct)
        ):
            raise ValidationError(_("You cannot assign other types of products"))

    def _check_valid_lease(self) -> None:
        # Check that only Berth or Winter leases are passed (not other models)
        if not isinstance(self.lease, (BerthLease, WinterStorageLease)):
            raise ValidationError(_("You cannot assign other types of leases"))

        # Check that the lease customer and the received customer are the same
        if self.lease.customer != self.customer:
            raise ValidationError(
                _("The lease provided belongs to a different customer")
            )

    def _check_product_and_lease(self) -> None:
        if isinstance(self.product, BerthProduct) and not isinstance(
            self.lease, BerthLease
        ):
            raise ValidationError(
                _("A BerthProduct must be associated with a BerthLease")
            )
        elif isinstance(self.product, WinterStorageProduct) and not isinstance(
            self.lease, WinterStorageLease
        ):
            raise ValidationError(
                _("A WinterStorageProduct must be associated with a WinterStorageLease")
            )

    def _check_product_or_price(self) -> None:
        if all([not self.product, not self._product_object_id, not self.price]):
            raise ValidationError(
                _("Order must have either product object or price value")
            )

    def _check_same_product(self, old_instance) -> None:
        if old_instance.product and self.product != old_instance.product:
            raise ValidationError(_("Cannot change the product assigned to this order"))

    def _check_same_lease(self, old_instance) -> None:
        if old_instance.lease and self.lease != old_instance.lease:
            raise ValidationError(
                _("Cannot change the lease associated with this order")
            )

    def clean(self):
        # Check that only Berth or Winter products are passed (not other models)
        self._check_valid_products()

        if self.lease:
            self._check_valid_lease()

            # Check that product and lease are from the same type
            if self.product:
                self._check_product_and_lease()

        # Check that it has either product or price
        self._check_product_or_price()

        if not self._state.adding:
            old_instance = Order.objects.get(id=self.id)
            # If the product is being changed
            self._check_same_product(old_instance)

            # If the lease is being changed
            self._check_same_lease(old_instance)

    def _create_order_lines(self, section):
        for service in ProductServiceType.FIXED_SERVICES():
            # If the section has the service (prop) and it's valid (True)
            if hasattr(section, service.name.lower()) and getattr(
                section, service.name.lower()
            ):
                # Retrieve the product for that service
                product = AdditionalProduct.objects.get(
                    service=service, period=PeriodType.SEASON
                )

                OrderLine.objects.create(
                    order=self, product=product,
                )

    def _assign_product_from_object_id(self):
        # Try to get a BerthProduct (BP)
        product = BerthProduct.objects.filter(id=self._product_object_id).first()
        # If the BP was not found, try getting a WinterStorageProduct
        product = (
            product
            if product
            else WinterStorageProduct.objects.filter(id=self._product_object_id).first()
        )
        # If for some reason neither was found (shouldn't be the case), raise an error
        if not product:
            raise ValidationError(_("The product passed is not valid"))

        self.product = product

    def _assign_lease_from_object_id(self):
        # Try to get a BerthLease (BL)
        lease = BerthLease.objects.filter(id=self._lease_object_id).first()
        # If the BL was not found, try getting a WinterStorageLease
        lease = (
            lease
            if lease
            else WinterStorageLease.objects.filter(id=self._lease_object_id).first()
        )
        # If for some reason neither was found, raise an error
        if not lease:
            raise ValidationError(_("The lease passed is not valid"))

        self.lease = lease

    def save(self, *args, **kwargs):
        self.full_clean()

        # If the product is being added from the admin (only the ID is passed)
        if self._product_object_id and not self.product:
            self._assign_product_from_object_id()

        # If the lease is being added from the admin (only the ID is passed)
        if self._lease_object_id and not self.lease:
            self._assign_lease_from_object_id()

        creating = self._state.adding
        # If the product instance is being passed
        # Price has to be assigned before saving but only if creating
        if creating and self.product:
            # Assign the price and tax from the product
            price = self.product.price_value
            tax_percentage = self.product.tax_percentage

            if self.lease:
                price = calculate_product_partial_season_price(
                    price,
                    self.lease.start_date,
                    self.lease.end_date,
                    summer_season=isinstance(self.lease, BerthLease),
                )

                # If the order is for a winter product with a lease, the price
                # has to be calculated based on the dimensions of the place associated
                # to the lease
                if isinstance(self.lease, WinterStorageLease) and isinstance(
                    self.product, WinterStorageProduct
                ):
                    place_sqm = (
                        self.lease.place.place_type.width
                        * self.lease.place.place_type.length
                    )
                    price = price * place_sqm

            self.price = rounded_decimal(self.price or price)
            self.tax_percentage = self.tax_percentage or tax_percentage

        old_instance = Order.objects.filter(id=self.id).first()
        # Save before adding additional products to have access to self
        super().save(*args, **kwargs)

        # Create OrderLines for the corresponding services only:
        #   - If it's creating the order
        #   - If the previous lease value was None (setting a lease)
        # For now, it only applies BerthLeases, since WinterStorageLeases include the
        # services on the m2 price.
        if (creating or (old_instance and not old_instance.lease)) and isinstance(
            self.lease, BerthLease
        ):
            self._create_order_lines(self.lease.berth.pier)


class OrderLine(UUIDModel, TimeStampedModel):
    order = models.ForeignKey(
        Order,
        verbose_name=_("order"),
        related_name="order_lines",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        AdditionalProduct,
        verbose_name=_("product"),
        related_name="orders_lines",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    quantity = models.PositiveSmallIntegerField(
        verbose_name=_("quantity"), default=1, validators=[MinValueValidator(1)],
    )
    price = models.DecimalField(
        verbose_name=_("price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        blank=True,
    )
    tax_percentage = models.DecimalField(
        verbose_name=_("tax percentage"),
        max_digits=5,
        decimal_places=2,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    def clean(self):
        creating = self._state.adding
        if not creating:
            old_instance = OrderLine.objects.get(id=self.id)
            # If the order is being changed
            if old_instance.order and self.order != old_instance.order:
                raise ValidationError(
                    _("Cannot change the order associated with this order line")
                )

            # If the product is being changed
            if old_instance.product != self.product:
                raise ValidationError(
                    _("Cannot change the product assigned to this order line")
                )

    def save(self, *args, **kwargs):
        self.full_clean()

        creating = self._state.adding
        if creating and self.product:
            price = self.product.price_value
            unit = self.product.price_unit

            if not self.price:
                if unit == PriceUnits.PERCENTAGE:
                    price = calculate_product_percentage_price(
                        self.order.price, self.product.price_value
                    )

                if self.order.lease:
                    if self.product.period == PeriodType.MONTH:
                        price = calculate_product_partial_month_price(
                            price,
                            self.order.lease.start_date,
                            self.order.lease.end_date,
                        )
                    elif self.product.period == PeriodType.SEASON:
                        # Calculate the actual price for the amount of days on the period
                        # price = (days_on_lease * product.price_value) / season_days
                        price = calculate_product_partial_season_price(
                            price,
                            self.order.lease.start_date,
                            self.order.lease.end_date,
                            summer_season=isinstance(self.order.lease, BerthLease),
                        )
                    elif self.product.period == PeriodType.YEAR:
                        price = calculate_product_partial_year_price(
                            price,
                            self.order.lease.start_date,
                            self.order.lease.end_date,
                        )
                self.price = price
            if not self.tax_percentage:
                self.tax_percentage = self.product.tax_percentage

        super().save(*args, **kwargs)

    @property
    @rounded
    def pretax_price(self):
        return convert_aftertax_to_pretax(self.price, self.tax_percentage)

    def __str__(self):
        return f"{self.order}  - {self.product}"


class OrderLogEntry(UUIDModel, TimeStampedModel):
    order = models.ForeignKey(
        Order,
        verbose_name=_("order log entry"),
        related_name="log_entries",
        on_delete=models.CASCADE,
    )
    status = EnumField(OrderStatus)
    comment = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = _("order log entries")
