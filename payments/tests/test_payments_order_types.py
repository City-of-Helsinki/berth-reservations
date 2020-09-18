import pytest  # noqa

from applications.enums import ApplicationAreaType
from applications.tests.factories import (
    BerthApplicationFactory,
    BerthSwitchFactory,
    WinterStorageApplicationFactory,
)
from leases.tests.factories import BerthLeaseFactory, WinterStorageLeaseFactory
from payments.enums import OrderType
from payments.tests.factories import (
    BerthProductFactory,
    OrderFactory,
    WinterStorageProductFactory,
)
from payments.tests.utils import random_price, random_tax


def test_order_type_new_berth_order(berth_lease, berth_product):
    order = OrderFactory(lease=berth_lease, product=berth_product)
    assert order.order_type == OrderType.NEW_BERTH_ORDER


def test_order_type_renew_berth_order(berth, customer_profile):
    BerthLeaseFactory(
        customer=customer_profile,
        berth=berth,
        start_date="2020-05-10",
        end_date="2020-05-15",
    )
    lease = BerthLeaseFactory(
        customer=customer_profile,
        berth=berth,
        start_date="2020-06-10",
        end_date="2020-06-15",
    )
    order = OrderFactory(
        lease=lease, customer=customer_profile, product=BerthProductFactory(),
    )
    assert order.order_type == OrderType.RENEW_BERTH_ORDER


def test_order_type_berth_switch_order(customer_profile):
    order = OrderFactory(
        customer=customer_profile,
        product=BerthProductFactory(),
        lease=BerthLeaseFactory(
            customer=customer_profile,
            application=BerthApplicationFactory(berth_switch=BerthSwitchFactory()),
        ),
    )
    assert order.order_type == OrderType.BERTH_SWITCH_ORDER


def test_order_type_winter_storage_order(customer_profile):
    order = OrderFactory(
        customer=customer_profile,
        product=WinterStorageProductFactory(),
        lease=WinterStorageLeaseFactory(customer=customer_profile),
    )
    assert order.order_type == OrderType.WINTER_STORAGE_ORDER


def test_order_type_unmarked_winter_storage_order(customer_profile):
    order = OrderFactory(
        customer=customer_profile,
        product=WinterStorageProductFactory(),
        lease=WinterStorageLeaseFactory(
            customer=customer_profile,
            application=WinterStorageApplicationFactory(
                area_type=ApplicationAreaType.UNMARKED
            ),
        ),
    )
    assert order.order_type == OrderType.UNMARKED_WINTER_STORAGE_ORDER


def test_order_type_invalid(customer_profile):
    order = OrderFactory(
        lease=None, product=None, price=random_price(), tax_percentage=random_tax()
    )
    assert order.order_type == OrderType.INVALID
