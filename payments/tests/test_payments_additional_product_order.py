from decimal import Decimal

import pytest
from freezegun import freeze_time

from customers.schema import ProfileNode
from leases.enums import LeaseStatus
from leases.schema import BerthLeaseNode
from leases.tests.factories import BerthLeaseFactory
from utils.relay import to_global_id

from ..enums import OrderStatus, PeriodType, PriceUnits, ProductServiceType
from ..models import Order, OrderLine
from ..schema.types import AdditionalProductNode
from .factories import (
    BerthProductFactory,
    OrderFactory,
    OrderLineFactory,
    PlainAdditionalProductFactory,
)
from .utils import get_berth_lease_pricing_category

CREATE_ADDITIONAL_PRODUCT_ORDER_MUTATION = """
mutation CREATE_ADDITIONAL_PRODUCT_ORDER($input: CreateAdditionalProductOrderMutationInput!) {
  createAdditionalProductOrder(input: $input) {
    order {
      id
      price
      totalPrice
      taxPercentage
      customer {
        id
      }
      product {
        ... on BerthProductNode {
          id
        }
        ... on WinterStorageProductNode {
          id
        }
      }
      lease {
        ... on BerthLeaseNode {
          id
        }
      }
      orderLines {
        edges {
          node {
            quantity
            price
            taxPercentage
            product {
              id
            }
          }
        }
      }
    }
  }
}
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_create_additional_product_order(api_client):
    berth_lease = BerthLeaseFactory(create_product=False, status=LeaseStatus.PAID)
    # Setup the existing order and lease
    BerthProductFactory(
        min_width=berth_lease.berth.berth_type.width - 1,
        max_width=berth_lease.berth.berth_type.width + 1,
        tier_1_price=Decimal("200.00"),
        tier_2_price=Decimal("200.00"),
        tier_3_price=Decimal("200.00"),
        price_unit=PriceUnits.AMOUNT,
        tax_percentage=Decimal("24.00"),
        pricing_category=get_berth_lease_pricing_category(berth_lease),
    )
    order = OrderFactory(
        lease=berth_lease,
        product=None,
        price=Decimal("0.00"),
        tax_percentage=Decimal("0.00"),
        status=OrderStatus.PAID,
    )
    # Optional services should be not included in the base price for additional product order
    extra_service = PlainAdditionalProductFactory(
        service=ProductServiceType.PARKING_PERMIT,
        price_unit=PriceUnits.AMOUNT,
        tax_percentage=Decimal("10.00"),
        period=PeriodType.SEASON,
    )
    OrderLineFactory(order=order, product=extra_service, price=Decimal("15.00"))
    # Fixed services should be included to the base price
    fixed_service = PlainAdditionalProductFactory(
        service=ProductServiceType.WASTE_COLLECTION,
        price_unit=PriceUnits.AMOUNT,
        tax_percentage=Decimal("24.00"),
        period=PeriodType.SEASON,
    )
    OrderLineFactory(order=order, product=fixed_service, price=Decimal("10.00"))

    # This is the additional product for the new order
    additional_product = PlainAdditionalProductFactory(
        service=ProductServiceType.STORAGE_ON_ICE,
        period=PeriodType.SEASON,
        tax_percentage=Decimal("24.00"),
        price_value=Decimal("60.00"),
        price_unit=PriceUnits.PERCENTAGE,
    )

    customer_id = to_global_id(ProfileNode, berth_lease.customer.id)
    additional_product_id = to_global_id(AdditionalProductNode, additional_product.id)
    lease_id = to_global_id(BerthLeaseNode, berth_lease.id)

    variables = {
        "customerId": customer_id,
        "additionalProductId": additional_product_id,
        "leaseId": lease_id,
    }

    assert Order.objects.count() == 1
    assert OrderLine.objects.count() == 2

    executed = api_client.execute(
        CREATE_ADDITIONAL_PRODUCT_ORDER_MUTATION, input=variables
    )
    assert Order.objects.count() == 2
    assert OrderLine.objects.count() == 3

    # 60 % of (lease order's base price (200) + lease order's fixed service (10))
    expected_total_price = "126.00"
    assert (
        executed["data"]["createAdditionalProductOrder"]["order"].pop("id") is not None
    )
    order_lines = executed["data"]["createAdditionalProductOrder"]["order"].pop(
        "orderLines"
    )

    assert executed["data"]["createAdditionalProductOrder"]["order"] == {
        "price": "0.00",
        "totalPrice": expected_total_price,
        "taxPercentage": "0.00",
        "customer": {"id": customer_id},
        "product": None,
        "lease": {"id": lease_id},
    }

    assert len(order_lines["edges"]) == 1
    assert order_lines["edges"][0]["node"] == {
        "quantity": 1,
        "price": expected_total_price,
        "taxPercentage": "24.00",
        "product": {"id": additional_product_id},
    }
