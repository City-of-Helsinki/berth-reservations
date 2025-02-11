import random

import pytest
from dateutil.relativedelta import relativedelta
from dateutil.utils import today

from berth_reservations.tests.utils import (
    assert_doesnt_exist,
    assert_not_enough_permissions,
    create_api_client,
)
from customers.schema import ProfileNode
from leases.models import BerthLease, WinterStorageLease
from leases.schema import BerthLeaseNode, WinterStorageLeaseNode
from resources.schema import WinterStorageAreaNode
from utils.relay import to_global_id

from ..enums import OfferStatus, OrderStatus, OrderType, ProductServiceType
from ..models import BerthProduct, Order, WinterStorageProduct
from ..schema.types import (
    AdditionalProductNode,
    AdditionalProductTaxEnum,
    AdditionalProductTypeEnum,
    BerthProductNode,
    OfferStatusEnum,
    OrderLineNode,
    OrderLogEntryNode,
    OrderNode,
    OrderRefundNode,
    OrderStatusEnum,
    OrderTypeEnum,
    PeriodTypeEnum,
    PlaceProductTaxEnum,
    PriceUnitsEnum,
    ProductServiceTypeEnum,
    WinterStorageProductNode,
)
from ..utils import generate_order_number
from .factories import (
    AdditionalProductFactory,
    BerthProductFactory,
    OrderFactory,
    OrderLineFactory,
    OrderLogEntryFactory,
    OrderRefundFactory,
    WinterStorageProductFactory,
)

BERTH_PRODUCTS_QUERY = """
query BERTH_PRODUCTS {
    berthProducts {
        edges {
            node {
                id
                minWidth
                maxWidth
                tier1Price
                tier2Price
                tier3Price
                priceUnit
                taxPercentage
           }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_supervisor", "berth_handler", "berth_services"],
    indirect=True,
)
def test_get_berth_products(api_client, berth_product):
    executed = api_client.execute(BERTH_PRODUCTS_QUERY)

    assert executed["data"]["berthProducts"]["edges"][0]["node"] == {
        "id": to_global_id(BerthProductNode, berth_product.id),
        "minWidth": str(berth_product.min_width),
        "maxWidth": str(berth_product.max_width),
        "tier1Price": str(berth_product.tier_1_price),
        "tier2Price": str(berth_product.tier_2_price),
        "tier3Price": str(berth_product.tier_3_price),
        "priceUnit": berth_product.price_unit.name,
        "taxPercentage": PlaceProductTaxEnum.get(berth_product.tax_percentage).name,
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services"],
    indirect=True,
)
def test_get_berth_products_not_enough_permissions(api_client):
    executed = api_client.execute(BERTH_PRODUCTS_QUERY)

    assert_not_enough_permissions(executed)


BERTH_PRODUCT_QUERY = """
query BERTH_PRODUCT {
    berthProduct(id: "%s") {
        id
        minWidth
        maxWidth
        tier1Price
        tier2Price
        tier3Price
        priceUnit
        taxPercentage
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_supervisor", "berth_handler", "berth_services"],
    indirect=True,
)
def test_get_berth_product(api_client, berth_product):
    product_global_id = to_global_id(BerthProductNode, berth_product.id)
    executed = api_client.execute(BERTH_PRODUCT_QUERY % product_global_id)

    assert executed["data"]["berthProduct"] == {
        "id": product_global_id,
        "minWidth": str(berth_product.min_width),
        "maxWidth": str(berth_product.max_width),
        "tier1Price": str(berth_product.tier_1_price),
        "tier2Price": str(berth_product.tier_2_price),
        "tier3Price": str(berth_product.tier_3_price),
        "priceUnit": berth_product.price_unit.name,
        "taxPercentage": PlaceProductTaxEnum.get(berth_product.tax_percentage).name,
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services"],
    indirect=True,
)
def test_get_berth_product_not_enough_permissions(api_client, berth_product):
    product_global_id = to_global_id(BerthProductNode, berth_product.id)
    executed = api_client.execute(BERTH_PRODUCT_QUERY % product_global_id)

    assert_not_enough_permissions(executed)


BERTH_PRODUCT_FOR_WIDTH_QUERY = """
query BERTH_PRODUCT {
    berthProductForWidth(width: "%s") {
        id
        minWidth
        maxWidth
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_supervisor", "berth_handler", "berth_services"],
    indirect=True,
)
def test_get_berth_product_for_width(api_client):
    berth_product = BerthProductFactory(min_width="3.00", max_width="4.00")
    executed = api_client.execute(BERTH_PRODUCT_FOR_WIDTH_QUERY % "3.5")

    assert executed["data"]["berthProductForWidth"] == {
        "id": to_global_id(BerthProductNode, berth_product.id),
        "minWidth": str(berth_product.min_width),
        "maxWidth": str(berth_product.max_width),
    }


def test_get_berth_product_for_width_none_in_range(superuser_api_client):
    executed = superuser_api_client.execute(BERTH_PRODUCT_FOR_WIDTH_QUERY % "3.5")
    assert executed["data"]["berthProductForWidth"] is None


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services"],
    indirect=True,
)
def test_get_berth_product_for_width_not_enough_permissions(api_client):
    executed = api_client.execute(BERTH_PRODUCT_FOR_WIDTH_QUERY % "3.33")
    assert_not_enough_permissions(executed)


WINTER_STORAGE_PRODUCTS_QUERY = """
query WINTER_STORAGE_PRODUCTS {
    winterStorageProducts {
        edges {
            node {
                id
                priceValue
                priceUnit
                taxPercentage
                winterStorageArea {
                    id
                }
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_supervisor", "berth_handler", "berth_services"],
    indirect=True,
)
def test_get_winter_storage_products(api_client, winter_storage_product):
    executed = api_client.execute(WINTER_STORAGE_PRODUCTS_QUERY)

    assert executed["data"]["winterStorageProducts"]["edges"][0]["node"] == {
        "id": to_global_id(WinterStorageProductNode, winter_storage_product.id),
        "priceValue": str(winter_storage_product.price_value),
        "priceUnit": winter_storage_product.price_unit.name,
        "taxPercentage": PlaceProductTaxEnum.get(
            winter_storage_product.tax_percentage
        ).name,
        "winterStorageArea": {
            "id": to_global_id(
                WinterStorageAreaNode, winter_storage_product.winter_storage_area.id
            )
        },
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services"],
    indirect=True,
)
def test_get_winter_storage_products_not_enough_permissions(api_client):
    executed = api_client.execute(WINTER_STORAGE_PRODUCTS_QUERY)

    assert_not_enough_permissions(executed)


WINTER_STORAGE_PRODUCT_QUERY = """
query WINTER_STORAGE_PRODUCTS {
    winterStorageProduct(id: "%s") {
        id
        priceValue
        priceUnit
        taxPercentage
        winterStorageArea {
            id
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_supervisor", "berth_handler", "berth_services"],
    indirect=True,
)
def test_get_winter_storage_product(api_client, winter_storage_product):
    product_global_id = to_global_id(
        WinterStorageProductNode, winter_storage_product.id
    )
    executed = api_client.execute(WINTER_STORAGE_PRODUCT_QUERY % product_global_id)

    assert executed["data"]["winterStorageProduct"] == {
        "id": product_global_id,
        "priceValue": str(winter_storage_product.price_value),
        "priceUnit": winter_storage_product.price_unit.name,
        "taxPercentage": PlaceProductTaxEnum.get(
            winter_storage_product.tax_percentage
        ).name,
        "winterStorageArea": {
            "id": to_global_id(
                WinterStorageAreaNode, winter_storage_product.winter_storage_area.id
            )
        },
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services"],
    indirect=True,
)
def test_get_winter_storage_product_not_enough_permissions(
    api_client, winter_storage_product
):
    product_global_id = to_global_id(
        WinterStorageProductNode, winter_storage_product.id
    )
    executed = api_client.execute(WINTER_STORAGE_PRODUCT_QUERY % product_global_id)

    assert_not_enough_permissions(executed)


ADDITIONAL_PRODUCTS_QUERY = """
query ADDITIONAL_PRODUCTS {
    additionalProducts {
        edges {
            node {
                id
                service
                period
                priceValue
                priceUnit
                taxPercentage
                productType
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_supervisor", "berth_handler", "berth_services"],
    indirect=True,
)
def test_get_additional_products(api_client, additional_product):
    executed = api_client.execute(ADDITIONAL_PRODUCTS_QUERY)

    assert executed["data"]["additionalProducts"]["edges"][0]["node"] == {
        "id": to_global_id(AdditionalProductNode, additional_product.id),
        "service": ProductServiceTypeEnum.get(additional_product.service).name,
        "period": PeriodTypeEnum.get(additional_product.period).name,
        "priceValue": str(additional_product.price_value),
        "priceUnit": PriceUnitsEnum.get(additional_product.price_unit).name,
        "taxPercentage": AdditionalProductTaxEnum.get(
            additional_product.tax_percentage
        ).name,
        "productType": AdditionalProductTypeEnum.get(
            additional_product.product_type
        ).name,
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services"],
    indirect=True,
)
def test_get_additional_products_not_enough_permissions(api_client):
    executed = api_client.execute(ADDITIONAL_PRODUCTS_QUERY)

    assert_not_enough_permissions(executed)


ADDITIONAL_PRODUCTS_FILTERED_QUERY = """
query ADDITIONAL_PRODUCTS {
    additionalProducts(productType: %s) {
        edges {
            node {
                id
                productType
            }
        }
    }
}
"""


@pytest.mark.parametrize("filter", ["FIXED_SERVICE", "OPTIONAL_SERVICE"])
def test_get_additional_products_filtered(superuser_api_client, filter):
    fixed = AdditionalProductFactory(
        service=random.choice(ProductServiceType.FIXED_SERVICES())
    )
    optional = AdditionalProductFactory(
        service=random.choice(ProductServiceType.OPTIONAL_SERVICES())
    )

    executed = superuser_api_client.execute(ADDITIONAL_PRODUCTS_FILTERED_QUERY % filter)

    product = fixed if filter == "FIXED_SERVICE" else optional

    assert len(executed["data"]["additionalProducts"]) == 1
    assert executed["data"]["additionalProducts"]["edges"][0]["node"] == {
        "id": to_global_id(AdditionalProductNode, product.id),
        "productType": product.product_type.name,
    }


ADDITIONAL_PRODUCT_QUERY = """
query ADDITIONAL_PRODUCT {
    additionalProduct(id: "%s") {
        id
        service
        period
        priceValue
        priceUnit
        taxPercentage
        productType
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_supervisor", "berth_handler", "berth_services"],
    indirect=True,
)
def test_get_additional_product(api_client, additional_product):
    product_global_id = to_global_id(AdditionalProductNode, additional_product.id)
    executed = api_client.execute(ADDITIONAL_PRODUCT_QUERY % product_global_id)

    assert executed["data"]["additionalProduct"] == {
        "id": product_global_id,
        "service": ProductServiceTypeEnum.get(additional_product.service).name,
        "period": PeriodTypeEnum.get(additional_product.period).name,
        "priceValue": str(additional_product.price_value),
        "priceUnit": PriceUnitsEnum.get(additional_product.price_unit).name,
        "taxPercentage": AdditionalProductTaxEnum.get(
            additional_product.tax_percentage
        ).name,
        "productType": AdditionalProductTypeEnum.get(
            additional_product.product_type
        ).name,
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services"],
    indirect=True,
)
def test_get_additional_product_not_enough_permissions(api_client, additional_product):
    product_global_id = to_global_id(AdditionalProductNode, additional_product.id)
    executed = api_client.execute(ADDITIONAL_PRODUCT_QUERY % product_global_id)

    assert_not_enough_permissions(executed)


ORDERS_QUERY = """
query ORDERS {
    orders {
        edges {
            node {
                id
                price
                taxPercentage
                customer {
                    id
                }
                orderLines {
                    edges {
                        node {
                            id
                            product {
                                id
                            }
                        }
                    }
                }
                logEntries {
                    edges {
                        node {
                            id
                        }
                    }
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
                    ... on WinterStorageLeaseNode {
                        id
                    }
                }
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_supervisor", "berth_handler", "berth_services"],
    indirect=True,
)
@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
def test_get_orders(api_client, order):
    OrderLogEntryFactory(order=order)
    OrderLineFactory(order=order)

    order_lines = []
    for ol in order.order_lines.all():
        order_lines.append(
            {
                "node": {
                    "id": to_global_id(OrderLineNode, ol.id),
                    "product": {
                        "id": to_global_id(AdditionalProductNode, ol.product.id)
                    },
                }
            }
        )
    log_entries = []
    for le in order.log_entries.all():
        log_entries.append({"node": {"id": to_global_id(OrderLogEntryNode, le.id)}})

    product_id = to_global_id(
        (
            BerthProductNode
            if isinstance(order.product, BerthProduct)
            else WinterStorageProductNode
        ),
        order.product.id,
    )

    lease_id = None
    if isinstance(order.lease, BerthLease):
        lease_id = to_global_id(BerthLeaseNode, order.lease.id)
    elif isinstance(order.lease, WinterStorageLease):
        lease_id = to_global_id(WinterStorageLeaseNode, order.lease.id)

    executed = api_client.execute(ORDERS_QUERY)

    assert executed["data"]["orders"]["edges"][0]["node"] == {
        "id": to_global_id(OrderNode, order.id),
        "price": str(order.price),
        "taxPercentage": str(order.tax_percentage),
        "customer": {"id": to_global_id(ProfileNode, order.customer.id)},
        "orderLines": {"edges": order_lines},
        "logEntries": {"edges": log_entries},
        "product": {"id": product_id},
        "lease": {"id": lease_id},
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services"],
    indirect=True,
)
def test_get_orders_not_enough_permissions(api_client, order):
    executed = api_client.execute(ORDERS_QUERY)
    assert_not_enough_permissions(executed)


ORDER_QUERY = """
query ORDER {
    order(id: "%s") {
        id
        price
        taxPercentage
        customer {
            id
        }
        orderLines {
            edges {
                node {
                    id
                    product {
                        id
                    }
                }
            }
        }
        logEntries {
            edges {
                node {
                    id
                }
            }
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
            ... on WinterStorageLeaseNode {
                id
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_supervisor", "berth_handler", "berth_services"],
    indirect=True,
)
@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
def test_get_order(api_client, order):
    order_global_id = to_global_id(OrderNode, order.id)

    OrderLogEntryFactory(order=order)
    OrderLineFactory(order=order)

    order_lines = []
    for ol in order.order_lines.all():
        order_lines.append(
            {
                "node": {
                    "id": to_global_id(OrderLineNode, ol.id),
                    "product": {
                        "id": to_global_id(AdditionalProductNode, ol.product.id)
                    },
                }
            }
        )
    log_entries = []
    for le in order.log_entries.all():
        log_entries.append({"node": {"id": to_global_id(OrderLogEntryNode, le.id)}})

    product_id = to_global_id(
        (
            BerthProductNode
            if isinstance(order.product, BerthProduct)
            else WinterStorageProductNode
        ),
        order.product.id,
    )

    lease_id = None
    if isinstance(order.lease, BerthLease):
        lease_id = to_global_id(BerthLeaseNode, order.lease.id)
    elif isinstance(order.lease, WinterStorageLease):
        lease_id = to_global_id(WinterStorageLeaseNode, order.lease.id)

    executed = api_client.execute(ORDER_QUERY % order_global_id)

    assert executed["data"]["order"] == {
        "id": order_global_id,
        "price": str(order.price),
        "taxPercentage": str(order.tax_percentage),
        "customer": {"id": to_global_id(ProfileNode, order.customer.id)},
        "orderLines": {"edges": order_lines},
        "logEntries": {"edges": log_entries},
        "product": {"id": product_id},
        "lease": {"id": lease_id},
    }


ORDER_QUERY_DUE_DATE = """
query ORDER {
    order(id: "%s") {
        id
        dueDate
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_supervisor", "berth_handler", "berth_services"],
    indirect=True,
)
def test_get_order_without_due_date(api_client, order):
    order.due_date = None
    order.status = OrderStatus.DRAFTED
    order.save()
    order_global_id = to_global_id(OrderNode, order.id)

    executed = api_client.execute(ORDER_QUERY_DUE_DATE % order_global_id)

    assert executed["data"]["order"] == {
        "id": order_global_id,
        "dueDate": None,
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services"],
    indirect=True,
)
def test_get_order_not_enough_permissions(api_client, order):
    order_global_id = to_global_id(OrderNode, order.id)

    executed = api_client.execute(ORDER_QUERY % order_global_id)

    assert_not_enough_permissions(executed)


ORDERS_FILTERED_QUERY = """
query ORDERS {
    orders(orderType: %s) {
        edges {
            node {
                id
            }
        }
    }
}
"""


@pytest.mark.parametrize("filter", ["BERTH", "WINTER_STORAGE"])
def test_get_orders_filtered(superuser_api_client, filter):
    berth_order = OrderFactory(product=BerthProductFactory())
    ws_order = OrderFactory(product=WinterStorageProductFactory())

    executed = superuser_api_client.execute(ORDERS_FILTERED_QUERY % filter)

    order = berth_order if filter == "BERTH" else ws_order

    assert len(executed["data"]["orders"]["edges"]) == 1
    assert executed["data"]["orders"]["edges"][0]["node"] == {
        "id": to_global_id(OrderNode, order.id)
    }


ORDER_DETAILS_QUERY = """
query ORDER_DETAILS {
    orderDetails(orderNumber: "%s") {
        orderType
        status
        place
        section
        area
        isApplicationOrder
    }
}
"""


@pytest.mark.parametrize(
    "order",
    [
        "berth_order",
        "winter_storage_order",
        "empty_order",
        "additional_product_order",
        "unmarked_winter_storage_order",
    ],
    indirect=True,
)
@pytest.mark.parametrize("has_application", [True, False])
@pytest.mark.parametrize("status", OrderStatus.values)
def test_get_order_status(
    superuser_api_client, status, has_application: bool, order: Order
):
    if not has_application and order.lease:
        order.lease.application = None
        order.lease.save()

    order.status = status
    order.save()

    executed = superuser_api_client.execute(ORDER_DETAILS_QUERY % order.order_number)

    if order.order_type == OrderType.ADDITIONAL_PRODUCT_ORDER:
        order_type = OrderTypeEnum.ADDITIONAL_PRODUCT
    elif order.product:
        if isinstance(order.product, BerthProduct):
            order_type = OrderTypeEnum.BERTH
        elif isinstance(order.product, WinterStorageProduct):
            order_type = OrderTypeEnum.WINTER_STORAGE
    else:
        order_type = OrderTypeEnum.UNKNOWN

    if isinstance(order.lease, BerthLease):
        place_number = order.lease.berth.number
        section_identifier = order.lease.berth.pier.identifier
        area_name = order.lease.berth.pier.harbor.name
    elif isinstance(order.lease, WinterStorageLease):
        if order.lease.place:
            place_number = str(order.lease.place.number)
            section_identifier = order.lease.place.winter_storage_section.identifier
            area_name = order.lease.place.winter_storage_section.area.name
        else:
            place_number = None
            section_identifier = order.lease.section.identifier
            area_name = order.lease.section.area.name
    else:
        place_number = None
        section_identifier = None
        area_name = None

    assert executed["data"]["orderDetails"] == {
        "orderType": OrderTypeEnum.get(order_type).name,
        "status": OrderStatusEnum.get(order.status).name,
        "place": place_number,
        "section": section_identifier,
        "area": area_name,
        "isApplicationOrder": has_application and order.lease is not None,
    }


def test_get_order_status_order_does_not_exist(superuser_api_client):
    executed = superuser_api_client.execute(
        ORDER_DETAILS_QUERY % generate_order_number()
    )

    assert_doesnt_exist("Order", executed)


OFFER_DETAILS_QUERY = """
query OFFER_DETAILS {
    offerDetails(offerNumber: "%s") {
        status
        berth
        pier
        harbor
    }
}
"""


@pytest.mark.parametrize("status", OfferStatus.values)
def test_get_offer_status(superuser_api_client, status, berth_switch_offer):
    berth_switch_offer.status = status
    berth_switch_offer.due_date = today() + relativedelta(weeks=2)
    berth_switch_offer.save()

    executed = superuser_api_client.execute(
        OFFER_DETAILS_QUERY % berth_switch_offer.offer_number
    )

    assert executed["data"]["offerDetails"] == {
        "status": OfferStatusEnum.get(berth_switch_offer.status).name,
        "berth": berth_switch_offer.berth.number,
        "pier": berth_switch_offer.berth.pier.identifier,
        "harbor": berth_switch_offer.berth.pier.harbor.name,
    }


def test_get_offer_status_order_does_not_exist(superuser_api_client):
    executed = superuser_api_client.execute(
        OFFER_DETAILS_QUERY % generate_order_number()
    )

    assert_doesnt_exist("BerthSwitchOffer", executed)


ORDERS_FILTERED_STATUS_QUERY = """
query ORDERS {
    orders(statuses: [%s]) {
        edges {
            node {
                id
                status
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order", "empty_order", "additional_product_order"],
    indirect=True,
)
@pytest.mark.parametrize("status", list(OrderStatus))
def test_get_orders_filtered_statuses(superuser_api_client, order, status):
    order.status = status
    order.save(update_fields=["status"])

    executed = superuser_api_client.execute(ORDERS_FILTERED_STATUS_QUERY % status.name)

    assert len(executed["data"]["orders"]["edges"]) == 1
    assert executed["data"]["orders"]["edges"][0]["node"] == {
        "id": to_global_id(OrderNode, order.id),
        "status": status.name,
    }


ORDER_REFUNDS_QUERY = """
query ORDER_REFUNDS {
    orderRefunds(orderId: "%s") {
        edges {
            node {
                id
                status
                refundId
                amount
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order", "empty_order", "additional_product_order"],
    indirect=True,
)
def test_get_order_refunds(superuser_api_client, order):
    order.status = OrderStatus.PAID
    order.save(update_fields=["status"])
    refund = OrderRefundFactory(order=order)

    executed = superuser_api_client.execute(
        ORDER_REFUNDS_QUERY % to_global_id(OrderNode, order.id)
    )

    assert len(executed["data"]["orderRefunds"]["edges"]) == 1
    assert executed["data"]["orderRefunds"]["edges"][0]["node"] == {
        "id": to_global_id(OrderRefundNode, refund.id),
        "status": refund.status.name,
        "refundId": refund.refund_id,
        "amount": str(order.price),
    }


CUSTOMER_OWN_ORDERS_QUERY = """
query ORDERS {
    orders {
        edges {
            node {
                id
                customer {
                    id
                }
            }
        }
    }
}
"""


def test_get_customer_own_orders(customer_profile):
    customer_order = OrderFactory(customer=customer_profile)
    OrderFactory()

    api_client = create_api_client(user=customer_profile.user)
    executed = api_client.execute(CUSTOMER_OWN_ORDERS_QUERY)

    assert Order.objects.count() == 2

    assert len(executed["data"]["orders"]["edges"]) == 1
    assert executed["data"]["orders"]["edges"][0]["node"] == {
        "id": to_global_id(OrderNode, customer_order.id),
        "customer": {"id": to_global_id(ProfileNode, customer_profile.id)},
    }
