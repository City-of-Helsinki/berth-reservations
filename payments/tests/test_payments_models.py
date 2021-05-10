import random
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils.timezone import now
from freezegun import freeze_time

from leases.enums import LeaseStatus
from leases.tests.factories import BerthLeaseFactory, WinterStorageLeaseFactory
from leases.utils import (
    calculate_berth_lease_end_date,
    calculate_berth_lease_start_date,
    calculate_winter_storage_lease_end_date,
    calculate_winter_storage_lease_start_date,
)
from resources.enums import BerthMooringType
from resources.tests.factories import (
    WinterStoragePlaceFactory,
    WinterStoragePlaceTypeFactory,
    WinterStorageSectionFactory,
)
from utils.numbers import rounded

from ..enums import (
    AdditionalProductType,
    OfferStatus,
    OrderStatus,
    PeriodType,
    PriceUnits,
    PricingCategory,
    ProductServiceType,
)
from ..models import (
    AdditionalProduct,
    BerthProduct,
    DEFAULT_TAX_PERCENTAGE,
    Order,
    OrderLine,
    OrderRefund,
)
from ..utils import (
    calculate_product_partial_month_price,
    calculate_product_partial_year_price,
    calculate_product_percentage_price,
)
from .factories import (
    AdditionalProductFactory,
    BerthProductFactory,
    BerthSwitchOfferFactory,
    OrderFactory,
    OrderLineFactory,
    WinterStorageProductFactory,
)
from .utils import random_bool, random_price, random_tax


def test_berth_product_invalid_price_unit():
    with pytest.raises(ValidationError) as exception:
        BerthProductFactory(price_unit=PriceUnits.PERCENTAGE)

    errors = str(exception.value)
    assert "percentage" in errors
    assert "is not a valid choice" in errors


def test_berth_product_invalid_tax():
    with pytest.raises(ValidationError) as exception:
        BerthProductFactory(tax_percentage=Decimal("10.00"))

    errors = str(exception.value)
    assert "tax_percentage" in errors
    assert "is not a valid choice" in errors


def test_winter_storage_product_invalid_price_unit():
    with pytest.raises(ValidationError) as exception:
        WinterStorageProductFactory(price_unit=PriceUnits.PERCENTAGE)

    errors = str(exception.value)
    assert "percentage" in errors
    assert "is not a valid choice" in errors


def test_winter_storage_product_invalid_tax():
    with pytest.raises(ValidationError) as exception:
        WinterStorageProductFactory(tax_percentage=Decimal("10.00"))

    errors = str(exception.value)
    assert "tax_percentage" in errors
    assert "is not a valid choice" in errors


def test_additional_product_product_type_fixed():
    product = AdditionalProductFactory(
        service=ProductServiceType.ELECTRICITY,
        tax_percentage=DEFAULT_TAX_PERCENTAGE,
        period=PeriodType.SEASON,
    )
    assert product.product_type == AdditionalProductType.FIXED_SERVICE


def test_additional_product_product_type_optional():
    product = AdditionalProductFactory(service=ProductServiceType.DINGHY_PLACE)
    assert product.product_type == AdditionalProductType.OPTIONAL_SERVICE


@pytest.mark.parametrize("service", ProductServiceType.OPTIONAL_SERVICES())
@pytest.mark.parametrize("period", PeriodType.values)
def test_additional_product_one_service_per_period(service, period):
    product = AdditionalProductFactory(service=service, period=period)

    with pytest.raises(IntegrityError) as exception:
        # Copy the product to a new identical one
        product.pk = None
        product.save()

    errors = str(exception.value)
    assert (
        'duplicate key value violates unique constraint "optional_services_per_period"'
        in errors
    )


@pytest.mark.parametrize("period", [PeriodType.MONTH, PeriodType.YEAR])
def test_additional_product_no_season(period):
    with pytest.raises(ValidationError) as exception:
        AdditionalProductFactory(
            service=ProductServiceType.ELECTRICITY,
            tax_percentage=DEFAULT_TAX_PERCENTAGE,
            period=period,
        )

    errors = str(exception.value)
    assert "Fixed services are only valid for season" in errors


def test_additional_product_fixed_service_tax_value():
    with pytest.raises(ValidationError) as exception:
        AdditionalProductFactory(
            service=random.choice(ProductServiceType.FIXED_SERVICES()),
            tax_percentage=Decimal("10.00"),
        )

    errors = str(exception.value)
    assert f"Fixed services must have VAT of {DEFAULT_TAX_PERCENTAGE}€" in errors


def test_order_berth_product_winter_storage_lease_raise_error():
    lease = WinterStorageLeaseFactory()
    with pytest.raises(ValidationError) as exception:
        Order.objects.create(
            product=BerthProductFactory(), lease=lease, customer=lease.customer
        )

    errors = str(exception.value)
    assert "A BerthProduct must be associated with a BerthLease" in errors


def test_order_winter_storage_product_berth_lease_raise_error():
    lease = BerthLeaseFactory()
    with pytest.raises(ValidationError) as exception:
        Order.objects.create(
            product=WinterStorageProductFactory(), lease=lease, customer=lease.customer
        )

    errors = str(exception.value)
    assert (
        "A WinterStorageProduct must be associated with a WinterStorageLease" in errors
    )


def test_order_retrieves_berth_product(berth_product, customer_profile):
    order = Order.objects.create(
        _product_object_id=berth_product.id, customer=customer_profile
    )
    assert order.product.id == berth_product.id
    assert order._product_content_type.name == berth_product._meta.verbose_name


def test_order_retrieves_winter_storage_product(
    winter_storage_product, customer_profile
):
    order = Order.objects.create(
        _product_object_id=winter_storage_product.id, customer=customer_profile
    )
    assert order.product.id == winter_storage_product.id
    assert order._product_content_type.name == winter_storage_product._meta.verbose_name


def test_order_raise_error_invalid_product_id(customer_profile):
    with pytest.raises(ValidationError) as exception:
        Order.objects.create(_product_object_id=uuid.uuid4(), customer=customer_profile)
    errors = str(exception.value)
    assert "The product passed is not valid" in errors


def test_order_raise_error_no_product_or_price(customer_profile):
    with pytest.raises(ValidationError) as exception:
        Order.objects.create(_product_object_id=None, customer=customer_profile)
    errors = str(exception.value)
    assert "Order must have either product object or price value" in errors


def test_order_retrieves_berth_lease(berth_lease, berth_product, customer_profile):
    order = Order.objects.create(
        _lease_object_id=berth_lease.id,
        customer=customer_profile,
        product=berth_product,
    )
    assert order.lease.id == berth_lease.id
    assert order._lease_content_type.name == berth_lease._meta.verbose_name


def test_order_retrieves_winter_storage_lease(
    winter_storage_lease, winter_storage_product, customer_profile
):
    order = Order.objects.create(
        _lease_object_id=winter_storage_lease.id,
        customer=customer_profile,
        product=winter_storage_product,
    )
    sqm = (
        winter_storage_lease.place.place_type.width
        * winter_storage_lease.place.place_type.length
    )
    expected_price = rounded(
        winter_storage_product.price_value * sqm, decimals=2, round_to_nearest=1
    )

    assert order.lease.id == winter_storage_lease.id
    assert order._lease_content_type.name == winter_storage_lease._meta.verbose_name
    assert order.price == expected_price


def test_order_berth_product_price(berth_product, customer_profile):
    order = OrderFactory(product=berth_product, customer=customer_profile)
    assert order.product == berth_product
    assert order.price == berth_product.price_for_tier(
        order.lease.berth.pier.price_tier
    )
    assert order.tax_percentage == berth_product.tax_percentage


def test_order_winter_storage_product_price(winter_storage_product, customer_profile):
    order = Order.objects.create(
        product=winter_storage_product, customer=customer_profile
    )
    assert order.product == winter_storage_product
    assert order.price == winter_storage_product.price_value
    assert order.tax_percentage == winter_storage_product.tax_percentage


def test_order_with_plain_price_and_tax(customer_profile):
    price = random_price()
    tax = random_tax()
    order = Order.objects.create(
        price=price, tax_percentage=tax, customer=customer_profile
    )
    assert order.product is None
    assert order.price == price
    assert order.tax_percentage == tax


def test_order_raise_error_berth_lease_and_different_customer(
    berth_lease, berth_product, customer_profile
):
    with pytest.raises(ValidationError) as exception:
        Order.objects.create(
            product=berth_product, lease=berth_lease, customer=customer_profile,
        )

    errors = str(exception.value)
    assert "The lease provided belongs to a different customer" in errors


def test_order_raise_error_winter_storage_lease_and_different_customer(
    winter_storage_lease, winter_storage_product, customer_profile
):
    with pytest.raises(ValidationError) as exception:
        Order.objects.create(
            product=winter_storage_product,
            lease=winter_storage_lease,
            customer=customer_profile,
        )

    errors = str(exception.value)
    assert "The lease provided belongs to a different customer" in errors


def test_order_berth_lease_right_price_for_full_season(berth):
    lease = BerthLeaseFactory(berth=berth)
    product = BerthProductFactory(
        min_width=lease.berth.berth_type.width - 1,
        max_width=lease.berth.berth_type.width + 1,
    )
    order = Order.objects.create(product=product, customer=lease.customer, lease=lease)

    assert order.lease.start_date == calculate_berth_lease_start_date()
    assert order.lease.end_date == calculate_berth_lease_end_date()


@freeze_time("2020-06-11T08:00:00Z")
def test_order_winter_storage_lease_right_price_for_full_season(winter_storage_area):
    services = {
        "summer_storage_for_docking_equipment": True,
        "summer_storage_for_trailers": random_bool(),
    }
    for service, create in services.items():
        if create:
            # Using PriceUnits.AMOUNT to simplify testing
            AdditionalProductFactory(
                service=ProductServiceType(service),
                price_value=Decimal("25.00"),
                price_unit=PriceUnits.AMOUNT,
            )

    section = WinterStorageSectionFactory(**services, area=winter_storage_area)
    lease = WinterStorageLeaseFactory(
        place=WinterStoragePlaceFactory(winter_storage_section=section)
    )
    product = WinterStorageProductFactory(
        winter_storage_area=winter_storage_area, price_value=Decimal("100.00")
    )
    order = Order.objects.create(product=product, customer=lease.customer, lease=lease)

    for service, create in services.items():
        if create:
            additional_product = AdditionalProduct.objects.filter(
                service=ProductServiceType(service),
                price_unit=PriceUnits.AMOUNT,
                period=PeriodType.SEASON,
            ).first()
            OrderLine.objects.create(order=order, product=additional_product)

    assert order.lease.start_date == calculate_winter_storage_lease_start_date()
    assert order.lease.end_date == calculate_winter_storage_lease_end_date()
    sqm = order.lease.place.place_type.width * order.lease.place.place_type.length

    expected_price = rounded(Decimal("100.00") * sqm, decimals=2, round_to_nearest=1)
    assert order.price == expected_price

    for service, created in services.items():
        if created:
            order_line = OrderLine.objects.filter(
                order=order, product__service=ProductServiceType(service)
            ).first()
            assert order_line.price == Decimal("25.00")


@freeze_time("2020-01-01T08:00:00Z")
def test_order_winter_storage_lease_right_price_for_partial_month(winter_storage_area,):
    services = {
        "summer_storage_for_docking_equipment": True,
        "summer_storage_for_trailers": random_bool(),
    }
    day_offset = 14
    for service, create in services.items():
        if create:
            # Using PriceUnits.AMOUNT to simplify testing
            AdditionalProductFactory(
                service=ProductServiceType(service),
                price_unit=PriceUnits.AMOUNT,
                period=PeriodType.MONTH,
            )

    section = WinterStorageSectionFactory(**services, area=winter_storage_area)
    lease = WinterStorageLeaseFactory(
        place=WinterStoragePlaceFactory(winter_storage_section=section),
        start_date=today(),
        end_date=today() + timedelta(days=day_offset),
    )
    product = WinterStorageProductFactory(winter_storage_area=winter_storage_area)
    order = Order.objects.create(product=product, customer=lease.customer, lease=lease)

    for service, create in services.items():
        if create:
            product = AdditionalProduct.objects.filter(
                service=ProductServiceType(service),
                price_unit=PriceUnits.AMOUNT,
                period=PeriodType.MONTH,
            ).first()
            OrderLine.objects.create(order=order, product=product)

    assert order.lease.start_date != calculate_berth_lease_start_date()
    assert order.lease.end_date != calculate_berth_lease_end_date()
    for service, created in services.items():
        if created:
            order_line = OrderLine.objects.filter(
                order=order, product__service=ProductServiceType(service)
            ).first()
            partial_product_price = calculate_product_partial_month_price(
                order_line.product.price_value,
                order.lease.start_date,
                order.lease.end_date,
            )
            order_price = order_line.price
            assert partial_product_price == order_price


@freeze_time("2020-01-01T08:00:00Z")
def test_order_winter_storage_lease_right_price_for_partial_months(
    winter_storage_area,
):
    services = {
        "summer_storage_for_docking_equipment": random_bool(),
        "summer_storage_for_trailers": True,
    }
    day_offset = 64
    for service, create in services.items():
        if create:
            # Using PriceUnits.AMOUNT to simplify testing
            AdditionalProductFactory(
                service=ProductServiceType(service),
                price_unit=PriceUnits.AMOUNT,
                period=PeriodType.MONTH,
            )

    section = WinterStorageSectionFactory(**services, area=winter_storage_area)
    lease = WinterStorageLeaseFactory(
        place=WinterStoragePlaceFactory(winter_storage_section=section),
        start_date=today(),
        end_date=today() + timedelta(days=day_offset),
    )
    product = WinterStorageProductFactory(winter_storage_area=winter_storage_area)
    order = Order.objects.create(product=product, customer=lease.customer, lease=lease)

    for service, create in services.items():
        if create:
            product = AdditionalProduct.objects.filter(
                service=ProductServiceType(service),
                price_unit=PriceUnits.AMOUNT,
                period=PeriodType.MONTH,
            ).first()
            OrderLine.objects.create(order=order, product=product)

    assert order.lease.start_date.month != order.lease.end_date.month

    for service, created in services.items():
        if created:
            order_line = OrderLine.objects.filter(
                order=order, product__service=ProductServiceType(service)
            ).first()
            partial_product_price = calculate_product_partial_month_price(
                order_line.product.price_value,
                order.lease.start_date,
                order.lease.end_date,
            )
            order_price = order_line.price
            assert partial_product_price == order_price


@freeze_time("2020-01-01T08:00:00Z")
def test_order_winter_storage_lease_right_price_for_partial_year(winter_storage_area,):
    services = {
        "summer_storage_for_docking_equipment": True,
        "summer_storage_for_trailers": random_bool(),
    }
    day_offset = 100
    for service, create in services.items():
        if create:
            # Using PriceUnits.AMOUNT to simplify testing
            AdditionalProductFactory(
                service=ProductServiceType(service),
                price_unit=PriceUnits.AMOUNT,
                period=PeriodType.YEAR,
            )

    section = WinterStorageSectionFactory(**services, area=winter_storage_area)
    lease = WinterStorageLeaseFactory(
        place=WinterStoragePlaceFactory(winter_storage_section=section),
        start_date=today(),
        end_date=today() + timedelta(days=day_offset),
    )
    product = WinterStorageProductFactory(winter_storage_area=winter_storage_area)
    order = Order.objects.create(product=product, customer=lease.customer, lease=lease)

    for service, create in services.items():
        if create:
            product = AdditionalProduct.objects.filter(
                service=ProductServiceType(service),
                price_unit=PriceUnits.AMOUNT,
                period=PeriodType.YEAR,
            ).first()
            OrderLine.objects.create(order=order, product=product)

    assert order.lease.start_date != calculate_berth_lease_start_date()
    assert order.lease.end_date != calculate_berth_lease_end_date()
    for service, created in services.items():
        if created:
            order_line = OrderLine.objects.filter(
                order=order, product__service=ProductServiceType(service)
            ).first()
            partial_product_price = calculate_product_partial_year_price(
                order_line.product.price_value,
                order.lease.start_date,
                order.lease.end_date,
            )
            order_price = order_line.price
            assert partial_product_price == order_price


def test_order_change_berth_product(customer_profile):
    order = Order.objects.create(
        product=BerthProductFactory(),
        customer=customer_profile,
        status=OrderStatus.DRAFTED,
    )
    new_product = BerthProductFactory()
    order.product = new_product
    order.save()
    assert order.product == new_product


@pytest.mark.parametrize(
    "status",
    [
        OrderStatus.EXPIRED,
        OrderStatus.CANCELLED,
        OrderStatus.PAID,
        OrderStatus.PAID_MANUALLY,
        OrderStatus.REJECTED,
        OrderStatus.ERROR,
    ],
)
def test_order_cannot_change_berth_product(status, customer_profile):
    order = Order.objects.create(
        product=BerthProductFactory(), customer=customer_profile, status=status
    )
    with pytest.raises(ValidationError) as exception:
        order.product = BerthProductFactory()
        order.save()

    errors = str(exception.value)
    assert "Cannot change the product assigned to this order" in errors


def test_order_cannot_change_winter_storage_product(customer_profile):
    order = Order.objects.create(
        product=WinterStorageProductFactory(),
        customer=customer_profile,
        status=OrderStatus.PAID,
    )
    with pytest.raises(ValidationError) as exception:
        order.product = WinterStorageProductFactory()
        order.save()

    errors = str(exception.value)
    assert "Cannot change the product assigned to this order" in errors


def test_order_cannot_change_berth_lease(berth_lease):
    order = Order.objects.create(
        product=BerthProductFactory(), lease=berth_lease, customer=berth_lease.customer,
    )
    with pytest.raises(ValidationError) as exception:
        order.lease = BerthLeaseFactory(customer=berth_lease.customer)
        order.save()

    errors = str(exception.value)
    assert "Cannot change the lease associated with this order" in errors


def test_order_cannot_change_winter_storage_lease(winter_storage_lease):
    order = Order.objects.create(
        product=WinterStorageProductFactory(),
        lease=winter_storage_lease,
        customer=winter_storage_lease.customer,
    )
    with pytest.raises(ValidationError) as exception:
        order.lease = WinterStorageLeaseFactory(customer=winter_storage_lease.customer)
        order.save()

    errors = str(exception.value)
    assert "Cannot change the lease associated with this order" in errors


def test_order_berth_lease_can_change_price(berth_lease):
    order = Order.objects.create(
        product=BerthProductFactory(), lease=berth_lease, customer=berth_lease.customer,
    )
    price = random_price()
    tax_percentage = random_tax()

    order.price = price
    order.tax_percentage = tax_percentage

    order.save()

    assert order.price == price
    assert order.tax_percentage == tax_percentage


def test_order_winter_storage_lease_can_change_price(winter_storage_lease):
    order = Order.objects.create(
        product=WinterStorageProductFactory(),
        lease=winter_storage_lease,
        customer=winter_storage_lease.customer,
    )
    price = random_price()
    tax_percentage = random_tax()

    order.price = price
    order.tax_percentage = tax_percentage

    order.save()

    assert order.price == price
    assert order.tax_percentage == tax_percentage


def test_order_pretax_price(order):
    assert order.pretax_price == round(
        order.price / (1 + (order.tax_percentage / 100)), 2
    )


def test_order_manager_only_berth_orders():
    OrderFactory(product=BerthProductFactory())
    OrderFactory(product=WinterStorageProductFactory())

    orders = Order.objects.berth_orders()
    assert orders.count() == 1

    for order in orders:
        assert order.lease.berth is not None


def test_order_manager_only_winter_storage_orders():
    OrderFactory(product=BerthProductFactory())
    OrderFactory(product=WinterStorageProductFactory())

    orders = Order.objects.winter_storage_orders()
    assert orders.count() == 1

    for order in Order.objects.winter_storage_orders():
        assert order.lease.place is not None


@pytest.mark.parametrize("period", ["month", "season", "year"])
def test_order_line_product_price(period):
    service = (
        random.choice(list(ProductServiceType))
        if period == "season"
        else random.choice(ProductServiceType.OPTIONAL_SERVICES())
    )
    product = AdditionalProductFactory(
        price_unit=PriceUnits.AMOUNT, period=PeriodType(period), service=service
    )
    order_line = OrderLineFactory(product=product)

    if product.period == PeriodType.MONTH:
        expected_price = calculate_product_partial_month_price(
            product.price_value,
            order_line.order.lease.start_date,
            order_line.order.lease.end_date,
        )
    elif product.period == PeriodType.SEASON:
        expected_price = product.price_value
    elif product.period == PeriodType.YEAR:
        expected_price = calculate_product_partial_year_price(
            product.price_value,
            order_line.order.lease.start_date,
            order_line.order.lease.end_date,
        )
    assert order_line.price == expected_price
    assert order_line.tax_percentage == product.tax_percentage


# Freezing time to avoid season price miscalculation
@freeze_time("2020-01-01T08:00:00Z")
def test_order_line_percentage_price():
    product = AdditionalProductFactory(price_unit=PriceUnits.PERCENTAGE)
    order_line = OrderLineFactory(
        product=product, order=OrderFactory(product=BerthProductFactory())
    )

    assert order_line.price == calculate_product_percentage_price(
        order_line.order.price, product.price_value
    )


def test_order_line_pretax_price(order_line):
    assert order_line.pretax_price == round(
        order_line.price / (1 + (order_line.tax_percentage / 100)), 2
    )


def test_order_tax_percentage():
    # Hard-code the base price. Base tax percentage currently is always 24%
    o = OrderFactory(price=Decimal("100.00"))

    # Create a product for an optional service
    ap = AdditionalProductFactory(
        service=ProductServiceType.PARKING_PERMIT,
        price_unit=PriceUnits.AMOUNT,
        tax_percentage=Decimal("10.00"),
    )

    # Hard-code the price of additional product to override model's save method
    OrderLineFactory(order=o, product=ap, price=Decimal("88.70"))

    # Calculations:
    # base product: pretax = 80.65, tax = 24.0%, tax amount = 19.35
    # order line: pretax = 80.64, tax = 10.0%, tax amount = 8.06
    # total tax should be: (24.0 + 10.0) / 2 == 17.0
    assert o.total_tax_percentage == Decimal("17.00")


def test_winter_season_price():
    start_date = today()
    end_date = start_date + relativedelta(days=15)

    # 1m2 place for simplicity
    place = WinterStoragePlaceFactory(
        place_type=WinterStoragePlaceTypeFactory(width=1, length=1)
    )

    product = WinterStorageProductFactory(price_value=Decimal("10"))
    lease = WinterStorageLeaseFactory(
        place=place, start_date=start_date, end_date=end_date
    )
    order = Order.objects.create(product=product, lease=lease, customer=lease.customer)
    assert order.price == Decimal("10.00")


@freeze_time("2020-10-01T08:00:00Z")
def test_berth_season_price(berth):
    start_date = today()
    end_date = start_date + relativedelta(days=15)

    price = Decimal("10")
    product = BerthProductFactory(
        tier_1_price=price,
        tier_2_price=price,
        tier_3_price=price,
        min_width=berth.berth_type.width - 1,
        max_width=berth.berth_type.width + 1,
    )
    lease = BerthLeaseFactory(berth=berth, start_date=start_date, end_date=end_date)
    order = Order.objects.create(product=product, lease=lease, customer=lease.customer)
    assert order.price == Decimal("10.00")


def test_order_winter_storage_lease_with_section_right_price(
    winter_storage_section, winter_storage_product, boat
):
    winter_storage_lease = WinterStorageLeaseFactory(
        place=None, section=winter_storage_section, customer=boat.owner, boat=boat
    )
    order = Order.objects.create(
        _lease_object_id=winter_storage_lease.id,
        customer=boat.owner,
        product=winter_storage_product,
    )
    sqm = boat.width * boat.length

    expected_price = rounded(winter_storage_product.price_value * sqm, decimals=2)

    assert order.lease.id == winter_storage_lease.id
    assert order._lease_content_type.name == winter_storage_lease._meta.verbose_name
    assert order.price == expected_price


def test_order_winter_storage_lease_without_boat_right_price(
    winter_storage_section,
    winter_storage_product,
    winter_storage_application,
    customer_profile,
):
    winter_storage_lease = WinterStorageLeaseFactory(
        place=None,
        section=winter_storage_section,
        customer=customer_profile,
        boat=None,
        application=winter_storage_application,
    )
    order = Order.objects.create(
        _lease_object_id=winter_storage_lease.id,
        customer=customer_profile,
        product=winter_storage_product,
    )
    sqm = winter_storage_application.boat_width * winter_storage_application.boat_length

    expected_price = rounded(winter_storage_product.price_value * sqm, decimals=2)

    assert order.lease.id == winter_storage_lease.id
    assert order._lease_content_type.name == winter_storage_lease._meta.verbose_name
    assert order.price == expected_price


def test_order_right_price_for_company(
    winter_storage_section, winter_storage_product, boat, company_customer
):
    boat.owner = company_customer
    # we don't use decimals for width and length in this unit test
    # it causes random rounding problems when asserting the double price
    boat.width = 1
    boat.length = 4
    boat.save()

    winter_storage_lease = WinterStorageLeaseFactory(
        place=None, section=winter_storage_section, customer=boat.owner, boat=boat
    )
    order = Order.objects.create(
        _lease_object_id=winter_storage_lease.id,
        customer=boat.owner,
        product=winter_storage_product,
    )
    sqm = boat.width * boat.length

    # expect double the price
    expected_price = winter_storage_product.price_value * sqm * 2

    assert order.price == expected_price
    assert order.tax_percentage == winter_storage_product.tax_percentage


def test_order_right_price_for_non_billable(
    winter_storage_section, winter_storage_product, boat, non_billable_customer
):
    boat.owner = non_billable_customer
    boat.save()

    winter_storage_lease = WinterStorageLeaseFactory(
        place=None, section=winter_storage_section, customer=boat.owner, boat=boat
    )
    order = Order.objects.create(
        _lease_object_id=winter_storage_lease.id,
        customer=boat.owner,
        product=winter_storage_product,
    )

    assert order.price == 0
    assert order.tax_percentage == 0


def test_order_line_product_price_for_company(
    berth_lease, berth_product, company_customer
):
    product = AdditionalProductFactory(
        price_unit=PriceUnits.AMOUNT,
        period=PeriodType("year"),
        service=ProductServiceType.PARKING_PERMIT,
    )

    order = Order.objects.create(
        _lease_object_id=berth_lease.id,
        _product_object_id=berth_product.id,
        customer=company_customer,
    )

    order_line = OrderLineFactory(product=product, order=order)

    expected_price = (
        calculate_product_partial_year_price(
            product.price_value,
            order_line.order.lease.start_date,
            order_line.order.lease.end_date,
        )
        * 2
    )  # expect double price

    assert order_line.price == expected_price
    assert order_line.tax_percentage == product.tax_percentage


def test_order_line_product_price_for_non_billable(
    berth_lease, berth_product, non_billable_customer
):
    product = AdditionalProductFactory(
        price_unit=PriceUnits.AMOUNT,
        period=PeriodType("year"),
        service=ProductServiceType.PARKING_PERMIT,
    )

    order = Order.objects.create(
        _lease_object_id=berth_lease.id,
        _product_object_id=berth_product.id,
        customer=non_billable_customer,
    )

    order_line = OrderLineFactory(product=product, order=order)

    assert order_line.price == 0
    assert order_line.tax_percentage == 0


def test_berth_product_range():
    """Test the berth product boundaries"""
    bp1 = BerthProductFactory(min_width=Decimal("0.00"), max_width=Decimal("2.00"))
    bp2 = BerthProductFactory(min_width=Decimal("2.00"), max_width=Decimal("2.75"))
    bp3 = BerthProductFactory(min_width=Decimal("2.75"), max_width=Decimal("3.00"))

    assert BerthProduct.objects.get_in_range(width=2) == bp1
    assert BerthProduct.objects.get_in_range(width=2.01) == bp2
    assert BerthProduct.objects.get_in_range(width=2.75) == bp2
    assert BerthProduct.objects.get_in_range(width=2.76) == bp3


def test_order_set_status_no_lease(berth):
    product = BerthProductFactory(min_width=1, max_width=5)
    order = OrderFactory(product=product, status=OrderStatus.OFFERED, lease=None,)

    order.set_status(OrderStatus.PAID)
    assert not order.lease
    assert order.status == OrderStatus.PAID


def test_order_set_status_no_application(berth):
    lease = BerthLeaseFactory(berth=berth, application=None, status=LeaseStatus.OFFERED)
    product = BerthProductFactory(
        min_width=lease.berth.berth_type.width - 1,
        max_width=lease.berth.berth_type.width + 1,
    )
    order = OrderFactory(
        product=product,
        customer=lease.customer,
        lease=lease,
        status=OrderStatus.OFFERED,
    )

    order.set_status(OrderStatus.PAID)
    assert order.status == OrderStatus.PAID
    assert order.lease.status == LeaseStatus.PAID


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order", "additional_product_order"],
    indirect=True,
)
@pytest.mark.parametrize(
    "from_status,to_status",
    [
        (OrderStatus.DRAFTED, OrderStatus.OFFERED),
        (OrderStatus.OFFERED, OrderStatus.PAID),
        (OrderStatus.OFFERED, OrderStatus.PAID_MANUALLY),
        (OrderStatus.ERROR, OrderStatus.PAID_MANUALLY),
        (OrderStatus.OFFERED, OrderStatus.REJECTED),
        (OrderStatus.ERROR, OrderStatus.CANCELLED),
        (OrderStatus.OFFERED, OrderStatus.CANCELLED),
    ],
)
@freeze_time("2020-01-01T08:00:00Z")
def test_order_status_dates(order, from_status, to_status):
    order.status = from_status
    order.save()

    order.set_status(to_status)
    assert order.status == to_status

    order = Order.objects.get(id=order.id)
    if to_status in OrderStatus.get_paid_statuses():
        assert order.paid_at == now()
        assert order.rejected_at is None
        assert order.cancelled_at is None
    elif to_status == OrderStatus.REJECTED:
        assert order.rejected_at == now()
        assert order.paid_at is None
        assert order.cancelled_at is None
    elif to_status == OrderStatus.CANCELLED:
        assert order.cancelled_at == now()
        assert order.paid_at is None
        assert order.rejected_at is None


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order", "additional_product_order"],
    indirect=True,
)
@pytest.mark.parametrize(
    "status", OrderStatus.get_waiting_statuses(),
)
@freeze_time("2020-01-01T08:00:00Z")
def test_order_status_dates_no_transitions(order, status):
    order.status = status
    order.save()

    order = Order.objects.get(id=order.id)
    assert order.paid_at is None
    assert order.rejected_at is None
    assert order.cancelled_at is None


@pytest.mark.parametrize(
    "status",
    [
        OrderStatus.DRAFTED,
        OrderStatus.OFFERED,
        OrderStatus.REJECTED,
        OrderStatus.CANCELLED,
        OrderStatus.EXPIRED,
        OrderStatus.ERROR,
        OrderStatus.REFUNDED,
    ],
)
def test_order_refund_cannot_refund_not_paid(order, status):
    order.status = status
    order.save()

    with pytest.raises(ValidationError) as exception:
        OrderRefund.objects.create(order=order, amount=order.price)

    errors = str(exception.value)
    assert "Cannot refund orders that are not paid" in errors


def test_order_due_date_has_to_be_set_for_order_in_offered_status(
    order, berth_product, customer_profile
):
    with pytest.raises(ValidationError) as exception:
        order.due_date = None
        order.status = OrderStatus.OFFERED
        order.save()

    errors = str(exception.value)
    assert "Order cannot be offered without a due date" in errors

    with pytest.raises(ValidationError) as exception:
        Order.objects.create(
            product=berth_product, customer=customer_profile, status=OrderStatus.OFFERED
        )

    errors = str(exception.value)
    assert "Order cannot be offered without a due date" in errors


@pytest.mark.parametrize(
    "status", [OfferStatus.CANCELLED, OfferStatus.DRAFTED],
)
def test_offer_due_date_not_required(berth_switch_offer, status):
    berth_switch_offer.status = status
    berth_switch_offer.due_date = None
    berth_switch_offer.save()
    assert berth_switch_offer.due_date is None


def test_offer_due_date_required(berth_switch_offer):
    berth_switch_offer.status = OfferStatus.DRAFTED
    berth_switch_offer.due_date = None
    berth_switch_offer.save()

    assert berth_switch_offer.due_date is None

    with pytest.raises(ValidationError) as exception:
        berth_switch_offer.set_status(OfferStatus.OFFERED)

    assert "The offer must have a due date before sending it" in str(exception)


@freeze_time("2020-06-11T08:00:00Z")
def test_berth_switch_offer_current_season():
    berth_switch_offer = BerthSwitchOfferFactory(
        lease__start_date=calculate_berth_lease_start_date(),
        lease__end_date=calculate_berth_lease_end_date(),
    )

    assert berth_switch_offer.lease.start_date == date(2020, 6, 11)


@freeze_time("2020-06-11T08:00:00Z")
def test_berth_switch_offer_another_season():
    with pytest.raises(ValidationError) as exception:
        BerthSwitchOfferFactory(
            lease__start_date=calculate_berth_lease_start_date()
            - relativedelta(years=1),
            lease__end_date=calculate_berth_lease_end_date() - relativedelta(years=1),
        )

    assert "The exchanged lease has to be from the current season" in str(exception)


@pytest.mark.parametrize(
    "lease_status",
    [
        LeaseStatus.DRAFTED,
        LeaseStatus.ERROR,
        LeaseStatus.EXPIRED,
        LeaseStatus.OFFERED,
        LeaseStatus.REFUSED,
        LeaseStatus.TERMINATED,
    ],
)
def test_berth_switch_offer_lease_not_paid(lease_status):
    with pytest.raises(ValidationError) as exception:
        BerthSwitchOfferFactory(lease__status=lease_status)

    assert "The associated lease must be paid" in str(exception)


def test_berth_switch_offer_lease_changed_status():
    offer = BerthSwitchOfferFactory(lease__status=LeaseStatus.PAID)
    offer.lease.status = LeaseStatus.TERMINATED
    offer.lease.save()

    offer.set_status(OfferStatus.CANCELLED)

    assert offer.status == OfferStatus.CANCELLED
    assert offer.lease.status == LeaseStatus.TERMINATED


@pytest.mark.parametrize(
    "width,length,expected_price",
    [
        (2.4, 6, 164),
        (2.5, 6, 171),
        (3.5, 12, 479),
        (3, 10, 342),
        (3, 8, 274),
        (4, 12, 547),
        (3.5, 10, 399),
        (4.5, 12, 616),
    ],
)
def test_marked_winter_storage_price_rounded(width, length, expected_price):
    """For a place of 2,4 x 6,0, with the regular price of 11,4e the actual
    price would be 164,16e.
    According to the pricing rules, the prices are "rounded" to the nearest integer,
    in this case 164,00e.

    Testing all the possible width-length-price combinations according to the pricing table.
    """
    lease = WinterStorageLeaseFactory(
        place__place_type__width=width, place__place_type__length=length
    )
    product = WinterStorageProductFactory(
        winter_storage_area=lease.place.winter_storage_section.area,
        price_value=Decimal("11.40"),
        tax_percentage=Decimal("24.00"),
    )
    order = OrderFactory(
        customer=lease.customer,
        lease=lease,
        product=product,
        price=None,
        tax_percentage=Decimal("24.00"),
    )
    assert order.price == Decimal(expected_price)


@pytest.mark.parametrize(
    "mooring_type,expected_price",
    [
        (BerthMooringType.DINGHY_PLACE, Decimal("62.00")),
        (BerthMooringType.TRAWLER_PLACE, Decimal("129.00")),
    ],
)
@pytest.mark.parametrize("berth_width", [0.1, 1, 2, 3, 4, 5, 999])
def test_order_berth_product_dingy(berth_width, mooring_type, expected_price):
    lease = BerthLeaseFactory(
        berth__berth_type__mooring_type=mooring_type,
        berth__berth_type__width=berth_width,
    )
    product = BerthProduct(
        min_width=Decimal("0"),
        max_width=Decimal("999.99"),
        tier_1_price=expected_price,
        tier_2_price=expected_price,
        tier_3_price=expected_price,
        pricing_category=PricingCategory.DINGHY,
    )
    order = OrderFactory(
        customer=lease.customer,
        lease=lease,
        product=product,
        price=None,
        tax_percentage=Decimal("24.00"),
    )
    assert order.price == expected_price


@pytest.mark.parametrize(
    "berth_width,expected_price",
    [
        (Decimal("2.5"), Decimal("100.00")),
        (Decimal("2.7"), Decimal("102.00")),
        (Decimal("3.0"), Decimal("129.00")),
        (Decimal("3.5"), Decimal("157.00")),
    ],
)
def test_order_berth_product_vasikkasaari(berth_width, expected_price):
    lease = BerthLeaseFactory(berth__berth_type__width=berth_width,)
    lease.berth.pier.harbor.create_translation("fi", name="Vasikkasaaren venesatama")
    product = BerthProduct(
        min_width=berth_width - Decimal("0.01"),
        max_width=berth_width,
        tier_1_price=expected_price,
        tier_2_price=expected_price,
        tier_3_price=expected_price,
        pricing_category=PricingCategory.VASIKKASAARI,
    )
    order = OrderFactory(
        customer=lease.customer,
        lease=lease,
        product=product,
        price=None,
        tax_percentage=Decimal("24.00"),
    )
    assert order.price == expected_price
