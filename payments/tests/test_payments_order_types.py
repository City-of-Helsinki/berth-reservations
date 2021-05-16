import pytest  # noqa

from applications.enums import ApplicationAreaType
from applications.tests.factories import (
    BerthApplicationFactory,
    BerthSwitchFactory,
    WinterStorageApplicationFactory,
)
from leases.tests.factories import BerthLeaseFactory, WinterStorageLeaseFactory
from payments.enums import LeaseOrderType, OrderType
from payments.tests.factories import OrderFactory
from payments.tests.utils import random_price, random_tax


def test_order_type_new_berth_order(berth_lease):
    order = OrderFactory(lease=berth_lease)
    assert order.lease_order_type == LeaseOrderType.NEW_BERTH_ORDER


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
    order = OrderFactory(lease=lease)
    assert order.lease_order_type == LeaseOrderType.RENEW_BERTH_ORDER


def test_order_type_berth_switch_order():
    order = OrderFactory(
        lease=BerthLeaseFactory(
            application=BerthApplicationFactory(berth_switch=BerthSwitchFactory()),
        ),
    )
    assert order.lease_order_type == LeaseOrderType.BERTH_SWITCH_ORDER


def test_order_type_winter_storage_order():
    order = OrderFactory(lease=WinterStorageLeaseFactory(),)
    assert order.lease_order_type == LeaseOrderType.WINTER_STORAGE_ORDER


def test_order_type_unmarked_winter_storage_order():
    order = OrderFactory(
        lease=WinterStorageLeaseFactory(
            application=WinterStorageApplicationFactory(
                area_type=ApplicationAreaType.UNMARKED
            ),
        ),
    )
    assert order.lease_order_type == LeaseOrderType.UNMARKED_WINTER_STORAGE_ORDER


def test_order_type_additional_product_order(berth, customer_profile):
    lease = BerthLeaseFactory(
        customer=customer_profile,
        berth=berth,
        start_date="2020-06-10",
        end_date="2020-06-15",
    )
    order = OrderFactory(
        order_type=OrderType.ADDITIONAL_PRODUCT_ORDER,
        lease=lease,
        price=random_price(),
        tax_percentage=random_tax(),
    )
    assert order.lease_order_type == LeaseOrderType.INVALID


def test_order_type_invalid(customer_profile):
    order = OrderFactory(
        lease=None, product=None, price=random_price(), tax_percentage=random_tax()
    )
    assert order.lease_order_type == LeaseOrderType.INVALID
