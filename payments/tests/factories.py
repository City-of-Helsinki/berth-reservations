import random
from datetime import date, timedelta

import factory

from applications.tests.factories import BerthApplicationFactory, BerthSwitchFactory
from berth_reservations.tests.factories import CustomerProfileFactory
from leases.enums import LeaseStatus
from leases.tests.factories import BerthLeaseFactory
from resources.tests.factories import BerthFactory, WinterStorageAreaFactory

from utils.numbers import rounded
from ..enums import (
    OfferStatus,
    OrderRefundStatus,
    OrderStatus,
    PeriodType,
    PriceUnits,
    PricingCategory,
    ProductServiceType,
)
from ..models import (
    AbstractBaseProduct,
    AbstractOffer,
    AbstractPlaceProduct,
    ADDITIONAL_PRODUCT_TAX_PERCENTAGES,
    AdditionalProduct,
    BerthProduct,
    BerthSwitchOffer,
    DEFAULT_TAX_PERCENTAGE,
    Order,
    OrderLine,
    OrderLogEntry,
    OrderRefund,
    PLACE_PRODUCT_TAX_PERCENTAGES,
    WinterStorageProduct,
)
from .utils import random_price, random_tax


class AbstractBaseProductFactory(factory.django.DjangoModelFactory):
    price_unit = factory.Faker("random_element", elements=PriceUnits.values)
    price_value = factory.LazyAttribute(
        lambda o: random_price()
        if o.price_unit == PriceUnits.AMOUNT
        else random_price(1, 100, decimals=0)
    )

    class Meta:
        model = AbstractBaseProduct


class AbstractPlaceProductFactory(factory.django.DjangoModelFactory):
    price_unit = factory.LazyFunction(lambda: PriceUnits.AMOUNT)
    tax_percentage = factory.Faker(
        "random_element", elements=PLACE_PRODUCT_TAX_PERCENTAGES
    )

    class Meta:
        model = AbstractPlaceProduct


class BerthProductFactory(factory.django.DjangoModelFactory):
    min_width = factory.LazyFunction(
        lambda: rounded(random.uniform(0, 8), round_to_nearest=0.05)
    )
    max_width = factory.LazyAttribute(
        lambda o: rounded(random.uniform(float(o.min_width), 10), round_to_nearest=0.05)
    )

    tier_1_price = factory.LazyFunction(lambda: random_price(1, 100, decimals=0))
    tier_2_price = factory.LazyFunction(lambda: random_price(1, 100, decimals=0))
    tier_3_price = factory.LazyFunction(lambda: random_price(1, 100, decimals=0))
    tax_percentage = factory.Faker(
        "random_element", elements=PLACE_PRODUCT_TAX_PERCENTAGES
    )
    pricing_category = PricingCategory.DEFAULT

    class Meta:
        model = BerthProduct
        django_get_or_create = ("min_width", "max_width", "pricing_category")


class WinterStorageProductFactory(
    AbstractBaseProductFactory, AbstractPlaceProductFactory
):
    price_unit = factory.LazyFunction(lambda: PriceUnits.AMOUNT)
    winter_storage_area = factory.SubFactory(WinterStorageAreaFactory)

    class Meta:
        model = WinterStorageProduct
        django_get_or_create = ("winter_storage_area",)


class AdditionalProductFactory(AbstractBaseProductFactory):
    service = factory.Faker("random_element", elements=ProductServiceType.values)
    period = factory.LazyFunction(lambda: PeriodType.SEASON)
    tax_percentage = factory.LazyFunction(lambda: DEFAULT_TAX_PERCENTAGE)

    # Because of the FIXED_SERVICE restrictions (only allowed to have 24% VAT)
    # the actual assignment of a random Tax value is done once the service has
    # been assigned to the model.
    @factory.post_generation
    def tax_percentage(self, created, extracted, **kwargs):
        if extracted:
            self.tax_percentage = extracted
        elif self.service in ProductServiceType.FIXED_SERVICES():
            self.tax_percentage = DEFAULT_TAX_PERCENTAGE
        else:
            self.tax_percentage = random.choice(ADDITIONAL_PRODUCT_TAX_PERCENTAGES)

    class Meta:
        model = AdditionalProduct
        django_get_or_create = ("service", "period")


# This is used in test_create_additional_product_order to avoid random failures.
# AdditionalProductFactory picks e.g. service sometimes randomly even when trying to
# set and save the model afterwards.
class PlainAdditionalProductFactory(AbstractBaseProductFactory):
    class Meta:
        model = AdditionalProduct


class OrderFactory(factory.django.DjangoModelFactory):
    customer_phone = factory.Faker("phone_number", locale="fi_FI")
    status = factory.Faker(
        "random_element",
        elements=list(
            filter(lambda os: os is not OrderStatus.EXPIRED.value, OrderStatus.values)
        ),
    )
    due_date = date.today() + timedelta(days=14)
    comment = factory.Faker("sentence")

    @factory.lazy_attribute
    def customer(self):
        if hasattr(self, "lease") and self.lease is not None:
            return self.lease.customer
        return CustomerProfileFactory()

    @factory.lazy_attribute
    def price(self):
        if not getattr(self, "lease", None):
            return random_price()

    @factory.lazy_attribute
    def tax_percentage(self):
        if not getattr(self, "lease", None):
            return random_tax()

    class Meta:
        model = Order


class OrderLineFactory(factory.django.DjangoModelFactory):
    order = factory.SubFactory(OrderFactory)
    product = factory.SubFactory(AdditionalProductFactory)
    tax_percentage = factory.Faker(
        "random_element", elements=ADDITIONAL_PRODUCT_TAX_PERCENTAGES
    )

    class Meta:
        model = OrderLine

    @factory.post_generation
    def price(self, create, extracted, **kwargs):
        if extracted:
            self.price = extracted
        elif not self.price and not self.product:
            self.price = random_price()


class OrderLogEntryFactory(factory.django.DjangoModelFactory):
    order = factory.SubFactory(OrderFactory)
    from_status = factory.Faker("random_element", elements=OrderStatus.values)
    # This ensures that the status are always different
    to_status = factory.LazyAttribute(
        lambda ole: random.choice(
            list(filter(lambda s: s is not ole.from_status, OrderStatus.values))
        )
    )
    comment = factory.Faker("sentence")

    class Meta:
        model = OrderLogEntry


class AbstractOfferFactory(factory.django.DjangoModelFactory):
    customer = factory.SubFactory(CustomerProfileFactory, user=None)
    status = factory.LazyFunction(lambda: OfferStatus.DRAFTED)
    customer_first_name = factory.Faker("first_name", locale="fi_FI")
    customer_last_name = factory.Faker("last_name", locale="fi_FI")
    customer_email = factory.LazyAttribute(
        lambda x: f"{x.customer_first_name.lower()}.{x.customer_last_name.lower()}@email.com"
    )
    customer_phone = factory.Faker("phone_number", locale="fi_FI")

    class Meta:
        model = AbstractOffer


class BerthSwitchOfferFactory(AbstractOfferFactory):
    lease = factory.SubFactory(
        BerthLeaseFactory,
        customer=factory.SelfAttribute("..customer"),
        status=LeaseStatus.PAID,
    )
    berth = factory.SubFactory(BerthFactory)
    application = factory.SubFactory(
        BerthApplicationFactory,
        berth_switch=factory.SubFactory(BerthSwitchFactory),
    )

    class Meta:
        model = BerthSwitchOffer


class OrderRefundFactory(factory.django.DjangoModelFactory):
    order = factory.SubFactory(OrderFactory, status=OrderStatus.PAID)
    refund_id = factory.Sequence(lambda n: str(n))
    status = factory.LazyAttribute(lambda _: OrderRefundStatus.PENDING)
    amount = factory.SelfAttribute(".order.price")

    class Meta:
        model = OrderRefund
