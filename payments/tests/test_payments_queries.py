from decimal import Decimal

import pytest

from berth_reservations.tests.utils import assert_not_enough_permissions
from payments.tests.factories import BerthProductFactory
from resources.schema import HarborNode
from utils.relay import to_global_id

from ..schema.types import BerthPriceGroupNode, BerthProductNode

BERTH_PRICE_GROUPS_QUERY = """
query BERTH_PRICE_GROUPS {
    berthPriceGroups {
        edges {
            node {
                id
                name
                defaultProduct {
                    id
                    priceValue
                    priceUnit
                    taxPercentage
                    harbor {
                        properties {
                            name
                        }
                    }
                }
                products {
                    edges {
                        node {
                            id
                            priceValue
                            priceUnit
                            taxPercentage
                            harbor {
                                properties {
                                    name
                                }
                            }
                        }
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
def test_get_berth_price_groups(api_client, berth_price_group):
    product = BerthProductFactory(price_group=berth_price_group, harbor=None)
    product_dict = {
        "id": to_global_id(BerthProductNode, product.id),
        "priceValue": str(product.price_value),
        "priceUnit": product.price_unit.name,
        "taxPercentage": str(Decimal(product.tax_percentage).quantize(Decimal("1.00"))),
        "harbor": None,
    }

    executed = api_client.execute(BERTH_PRICE_GROUPS_QUERY)

    assert executed["data"]["berthPriceGroups"]["edges"][0]["node"] == {
        "id": to_global_id(BerthPriceGroupNode, berth_price_group.id),
        "name": berth_price_group.name,
        "defaultProduct": product_dict,
        "products": {"edges": [{"node": product_dict}]},
    }


@pytest.mark.parametrize(
    "api_client", ["api_client", "user", "harbor_services"], indirect=True,
)
def test_get_berth_price_groups_not_enough_permissions(api_client, berth_price_group):
    executed = api_client.execute(BERTH_PRICE_GROUPS_QUERY)

    assert_not_enough_permissions(executed)


BERTH_PRICE_GROUP_QUERY = """
query BERTH_PRICE_GROUPS {
    berthPriceGroup(id: "%s") {
        id
        name
        defaultProduct {
            id
            priceValue
            priceUnit
            taxPercentage
            harbor {
                properties {
                    name
                }
            }
        }
        products {
            edges {
                node {
                    id
                    priceValue
                    priceUnit
                    taxPercentage
                    harbor {
                        properties {
                            name
                        }
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
def test_get_berth_price_group(api_client, berth_price_group):
    group_global_id = to_global_id(BerthPriceGroupNode, berth_price_group.id)

    product = BerthProductFactory(price_group=berth_price_group, harbor=None)
    product_dict = {
        "id": to_global_id(BerthProductNode, product.id),
        "priceValue": str(product.price_value),
        "priceUnit": product.price_unit.name,
        "taxPercentage": str(Decimal(product.tax_percentage).quantize(Decimal("1.00"))),
        "harbor": None,
    }

    executed = api_client.execute(BERTH_PRICE_GROUP_QUERY % group_global_id)

    assert executed["data"]["berthPriceGroup"] == {
        "id": group_global_id,
        "name": berth_price_group.name,
        "defaultProduct": product_dict,
        "products": {"edges": [{"node": product_dict}]},
    }


@pytest.mark.parametrize(
    "api_client", ["api_client", "user", "harbor_services"], indirect=True,
)
def test_get_berth_price_group_not_enough_permissions(api_client, berth_price_group):
    group_global_id = to_global_id(BerthPriceGroupNode, berth_price_group.id)
    executed = api_client.execute(BERTH_PRICE_GROUP_QUERY % group_global_id)

    assert_not_enough_permissions(executed)


BERTH_PRODUCTS_QUERY = """
query BERTH_PRODUCTS {
    berthProducts {
        edges {
            node {
                id
                priceValue
                priceUnit
                taxPercentage
                priceGroup {
                    name
                }
                harbor {
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
def test_get_berth_products(api_client, berth_product):
    executed = api_client.execute(BERTH_PRODUCTS_QUERY)

    assert executed["data"]["berthProducts"]["edges"][0]["node"] == {
        "id": to_global_id(BerthProductNode, berth_product.id),
        "priceValue": str(berth_product.price_value),
        "priceUnit": berth_product.price_unit.name,
        "taxPercentage": str(
            Decimal(berth_product.tax_percentage).quantize(Decimal("1.00"))
        ),
        "priceGroup": {"name": berth_product.price_group.name},
        "harbor": {"id": to_global_id(HarborNode, berth_product.harbor.id)},
    }


@pytest.mark.parametrize(
    "api_client", ["api_client", "user", "harbor_services"], indirect=True,
)
def test_get_berth_products_not_enough_permissions(api_client, berth_price_group):
    executed = api_client.execute(BERTH_PRODUCTS_QUERY)

    assert_not_enough_permissions(executed)


BERTH_PRODUCT_QUERY = """
query BERTH_PRODUCT {
    berthProduct(id: "%s") {
        id
        priceValue
        priceUnit
        taxPercentage
        priceGroup {
            name
        }
        harbor {
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
def test_get_berth_product(api_client, berth_product):
    product_global_id = to_global_id(BerthProductNode, berth_product.id)
    executed = api_client.execute(BERTH_PRODUCT_QUERY % product_global_id)

    assert executed["data"]["berthProduct"] == {
        "id": product_global_id,
        "priceValue": str(berth_product.price_value),
        "priceUnit": berth_product.price_unit.name,
        "taxPercentage": str(
            Decimal(berth_product.tax_percentage).quantize(Decimal("1.00"))
        ),
        "priceGroup": {"name": berth_product.price_group.name},
        "harbor": {"id": to_global_id(HarborNode, berth_product.harbor.id)},
    }


@pytest.mark.parametrize(
    "api_client", ["api_client", "user", "harbor_services"], indirect=True,
)
def test_get_berth_product_not_enough_permissions(api_client, berth_product):
    product_global_id = to_global_id(BerthProductNode, berth_product.id)
    executed = api_client.execute(BERTH_PRODUCT_QUERY % product_global_id)

    assert_not_enough_permissions(executed)
