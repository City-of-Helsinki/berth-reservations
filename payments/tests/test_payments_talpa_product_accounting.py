from decimal import Decimal

import pytest  # noqa

from leases.enums import LeaseStatus
from leases.models import BerthLease
from payments.enums import OrderStatus, OrderType, ProductServiceType, TalpaProductType
from payments.exceptions import TalpaProductAccountingNotFoundError
from payments.models import TalpaProductAccounting
from payments.tests.conftest import *  # noqa
from payments.tests.factories import OrderFactory, OrderLineFactory
from resources.enums import AreaRegion


@pytest.mark.parametrize(
    "order_with_products",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
@pytest.mark.parametrize("region", [AreaRegion.WEST, AreaRegion.EAST])
def test_product_order(order_with_products, region, default_talpa_product_accounting):
    if isinstance(order_with_products.lease, BerthLease):
        order_with_products.lease.berth.pier.harbor.region = region
        order_with_products.lease.berth.pier.harbor.save()
        area = order_with_products.lease.berth.pier.harbor
        expected_type = TalpaProductType.BERTH
    else:
        order_with_products.product.winter_storage_area.region = region
        order_with_products.product.winter_storage_area.save()
        area = order_with_products.product.winter_storage_area
        expected_type = TalpaProductType.WINTER

    acc = TalpaProductAccounting.objects.get_product_accounting_for_product(
        order_with_products.product, area
    )
    assert acc.region == region
    assert acc.product_type == expected_type


@pytest.mark.parametrize("region", [AreaRegion.WEST, AreaRegion.EAST])
def test_storage_on_ice_product_order(
    payment_provider,
    additional_product,
    berth_lease_without_product,
    region,
    default_talpa_product_accounting,
):
    berth_lease_without_product.berth.pier.harbor.region = region
    berth_lease_without_product.berth.pier.harbor.save()

    additional_product.service = ProductServiceType.STORAGE_ON_ICE
    additional_product.tax_percentage = Decimal("24.00")
    additional_product.save()

    OrderFactory(
        price=Decimal("0.00"),
        tax_percentage=Decimal("24.00"),
        product=None,
        lease=berth_lease_without_product,
        status=OrderStatus.PAID,
    )
    berth_lease_without_product.status = LeaseStatus.PAID
    berth_lease_without_product.save()

    additional_product_order = OrderFactory(
        order_type=OrderType.ADDITIONAL_PRODUCT_ORDER,
        lease=berth_lease_without_product,
        product=None,
        price=Decimal("0.00"),
        tax_percentage=Decimal("0.00"),
    )
    OrderLineFactory(
        order=additional_product_order,
        product=additional_product,
        price=Decimal("15.00"),
    )
    acc = TalpaProductAccounting.objects.get_product_accounting_for_product(
        additional_product, berth_lease_without_product.berth.pier.harbor
    )
    assert acc.region == region
    assert acc.product_type == TalpaProductType.WINTER


@pytest.mark.parametrize("region", [AreaRegion.WEST, AreaRegion.EAST])
def test_product_order_no_region(order, region, default_talpa_product_accounting):
    with pytest.raises(TalpaProductAccountingNotFoundError):
        TalpaProductAccounting.objects.get_product_accounting_for_product(
            order.product, None
        )
