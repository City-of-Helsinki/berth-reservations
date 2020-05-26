import random

import pytest

from berth_reservations.tests.utils import assert_not_enough_permissions
from payments.enums import ServiceType
from payments.tests.factories import AdditionalProductFactory, BerthProductFactory
from resources.schema import HarborNode, WinterStorageAreaNode
from utils.relay import to_global_id

from ..schema.types import (
    AdditionalProductNode,
    AdditionalProductTaxEnum,
    BerthPriceGroupNode,
    BerthProductNode,
    PlaceProductTaxEnum,
    WinterStorageProductNode,
)

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
        "taxPercentage": PlaceProductTaxEnum.get(product.tax_percentage).name,
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
        "taxPercentage": PlaceProductTaxEnum.get(product.tax_percentage).name,
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
        "taxPercentage": PlaceProductTaxEnum.get(berth_product.tax_percentage).name,
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
        "taxPercentage": PlaceProductTaxEnum.get(berth_product.tax_percentage).name,
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
    "api_client", ["api_client", "user", "harbor_services"], indirect=True,
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
    "api_client", ["api_client", "user", "harbor_services"], indirect=True,
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
        "service": additional_product.service.name,
        "period": additional_product.period.name,
        "priceValue": str(additional_product.price_value),
        "priceUnit": additional_product.price_unit.name,
        "taxPercentage": AdditionalProductTaxEnum.get(
            additional_product.tax_percentage
        ).name,
        "productType": additional_product.product_type.name,
    }


@pytest.mark.parametrize(
    "api_client", ["api_client", "user", "harbor_services"], indirect=True,
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
        service=random.choice(ServiceType.FIXED_SERVICES())
    )
    optional = AdditionalProductFactory(
        service=random.choice(ServiceType.OPTIONAL_SERVICES())
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
        "service": additional_product.service.name,
        "period": additional_product.period.name,
        "priceValue": str(additional_product.price_value),
        "priceUnit": additional_product.price_unit.name,
        "taxPercentage": AdditionalProductTaxEnum.get(
            additional_product.tax_percentage
        ).name,
        "productType": additional_product.product_type.name,
    }


@pytest.mark.parametrize(
    "api_client", ["api_client", "user", "harbor_services"], indirect=True,
)
def test_get_additional_product_not_enough_permissions(api_client, additional_product):
    product_global_id = to_global_id(AdditionalProductNode, additional_product.id)
    executed = api_client.execute(ADDITIONAL_PRODUCT_QUERY % product_global_id)

    assert_not_enough_permissions(executed)
