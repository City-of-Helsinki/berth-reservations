import random
import uuid

import pytest

from berth_reservations.tests.utils import (
    assert_doesnt_exist,
    assert_field_missing,
    assert_not_enough_permissions,
)
from payments.enums import PriceUnits
from resources.schema import HarborNode
from utils.relay import to_global_id

from ..models import BerthProduct, DEFAULT_TAX_PERCENTAGE
from ..schema.types import BerthPriceGroupNode, BerthProductNode, PlaceProductTaxEnum

CREATE_BERTH_PRODUCT_MUTATION = """
mutation CREATE_BERTH_PRODUCT($input: CreateBerthProductMutationInput!) {
    createBerthProduct(input: $input) {
        berthProduct {
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
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
def test_create_berth_product(api_client, berth_price_group, harbor):
    variables = {
        "priceValue": str(round(random.uniform(1, 999), 2)),
        "priceGroupId": to_global_id(BerthPriceGroupNode, berth_price_group.id),
        "harborId": to_global_id(HarborNode, harbor.id),
    }

    assert BerthProduct.objects.count() == 0

    executed = api_client.execute(CREATE_BERTH_PRODUCT_MUTATION, input=variables)

    assert BerthProduct.objects.count() == 1
    assert executed["data"]["createBerthProduct"]["berthProduct"].pop("id") is not None

    assert executed["data"]["createBerthProduct"]["berthProduct"] == {
        "priceValue": variables["priceValue"],
        "priceUnit": PriceUnits.AMOUNT.name,
        "priceGroup": {"name": berth_price_group.name},
        "taxPercentage": PlaceProductTaxEnum.get(DEFAULT_TAX_PERCENTAGE).name,
        "harbor": {"id": variables["harborId"]},
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_create_berth_product_not_enough_permissions(api_client):
    variables = {
        "priceValue": "1.00",
        "priceGroupId": to_global_id(BerthPriceGroupNode, uuid.uuid4()),
    }

    assert BerthProduct.objects.count() == 0

    executed = api_client.execute(CREATE_BERTH_PRODUCT_MUTATION, input=variables)

    assert BerthProduct.objects.count() == 0
    assert_not_enough_permissions(executed)


def test_create_berth_product_no_price_group_id(superuser_api_client):
    variables = {
        "priceValue": "1.00",
    }

    assert BerthProduct.objects.count() == 0

    executed = superuser_api_client.execute(
        CREATE_BERTH_PRODUCT_MUTATION, input=variables
    )

    assert BerthProduct.objects.count() == 0
    assert_field_missing("priceGroupId", executed)


def test_create_berth_product_no_price_value(superuser_api_client):
    variables = {
        "priceGroupId": to_global_id(BerthPriceGroupNode, uuid.uuid4()),
    }

    assert BerthProduct.objects.count() == 0

    executed = superuser_api_client.execute(
        CREATE_BERTH_PRODUCT_MUTATION, input=variables
    )

    assert BerthProduct.objects.count() == 0
    assert_field_missing("priceValue", executed)


def test_create_berth_product_price_group_does_not_exist(superuser_api_client):
    variables = {
        "priceGroupId": to_global_id(BerthPriceGroupNode, uuid.uuid4()),
        "priceValue": "1.00",
    }

    assert BerthProduct.objects.count() == 0

    executed = superuser_api_client.execute(
        CREATE_BERTH_PRODUCT_MUTATION, input=variables
    )

    assert BerthProduct.objects.count() == 0
    assert_doesnt_exist("BerthPriceGroup", executed)


DELETE_BERTH_PRODUCT_MUTATION = """
mutation DELETE_BERTH_PRODUCT($input: DeleteBerthProductMutationInput!) {
    deleteBerthProduct(input: $input) {
        clientMutationId
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
def test_delete_berth_product(api_client, berth_product):
    variables = {"id": to_global_id(BerthProductNode, berth_product.id)}
    assert BerthProduct.objects.count() == 1

    api_client.execute(DELETE_BERTH_PRODUCT_MUTATION, input=variables)

    assert BerthProduct.objects.count() == 0


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_delete_berth_product_not_enough_permissions(api_client, berth_product):
    variables = {"id": to_global_id(BerthProductNode, berth_product.id)}
    assert BerthProduct.objects.count() == 1

    executed = api_client.execute(DELETE_BERTH_PRODUCT_MUTATION, input=variables)

    assert BerthProduct.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_delete_berth_product_does_not_exist(superuser_api_client):
    variables = {"id": to_global_id(BerthProductNode, uuid.uuid4())}

    executed = superuser_api_client.execute(
        DELETE_BERTH_PRODUCT_MUTATION, input=variables
    )

    assert_doesnt_exist("BerthProduct", executed)


UPDATE_BERTH_PRODUCT_MUTATION = """
mutation UPDATE_BERTH_PRODUCT($input: UpdateBerthProductMutationInput!) {
    updateBerthProduct(input: $input) {
        berthProduct {
            id
            priceValue
            priceUnit
            priceGroup {
                name
            }
            harbor {
                id
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
def test_update_berth_product(api_client, berth_product, berth_price_group, harbor):
    variables = {
        "id": to_global_id(BerthProductNode, berth_product.id),
        "priceValue": str(round(random.uniform(1, 999), 2)),
        "priceGroupId": to_global_id(BerthPriceGroupNode, berth_price_group.id),
        "harborId": to_global_id(HarborNode, harbor.id),
    }

    assert BerthProduct.objects.count() == 1

    executed = api_client.execute(UPDATE_BERTH_PRODUCT_MUTATION, input=variables)

    assert BerthProduct.objects.count() == 1

    assert executed["data"]["updateBerthProduct"]["berthProduct"] == {
        "id": variables["id"],
        "priceValue": variables["priceValue"],
        "priceUnit": PriceUnits.AMOUNT.name,
        "priceGroup": {"name": berth_price_group.name},
        "harbor": {"id": variables["harborId"]},
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_update_berth_product_not_enough_permissions(api_client):
    variables = {
        "id": to_global_id(BerthProductNode, uuid.uuid4()),
    }
    executed = api_client.execute(UPDATE_BERTH_PRODUCT_MUTATION, input=variables)

    assert_not_enough_permissions(executed)


def test_update_berth_product_does_not_exist(superuser_api_client):
    variables = {
        "id": to_global_id(BerthProductNode, uuid.uuid4()),
    }
    executed = superuser_api_client.execute(
        UPDATE_BERTH_PRODUCT_MUTATION, input=variables
    )

    assert_doesnt_exist("BerthProduct", executed)


def test_update_berth_product_price_group_does_not_exist(
    superuser_api_client, berth_product
):
    variables = {
        "id": to_global_id(BerthProductNode, berth_product.id),
        "priceGroupId": to_global_id(BerthPriceGroupNode, uuid.uuid4()),
    }

    assert BerthProduct.objects.count() == 1

    executed = superuser_api_client.execute(
        UPDATE_BERTH_PRODUCT_MUTATION, input=variables
    )

    assert BerthProduct.objects.count() == 1
    assert_doesnt_exist("BerthPriceGroup", executed)
