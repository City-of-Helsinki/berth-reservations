import random
import uuid

import pytest

from berth_reservations.tests.utils import (
    assert_doesnt_exist,
    assert_field_missing,
    assert_not_enough_permissions,
)
from payments.enums import (
    AdditionalProductType,
    PeriodType,
    PriceUnits,
    ProductServiceType,
)
from resources.schema import HarborNode, WinterStorageAreaNode
from utils.relay import to_global_id

from ..models import BerthProduct, DEFAULT_TAX_PERCENTAGE, WinterStorageProduct
from ..schema.types import (
    ADDITIONAL_PRODUCT_TAX_PERCENTAGES,
    AdditionalProduct,
    AdditionalProductNode,
    AdditionalProductTaxEnum,
    BerthPriceGroupNode,
    BerthProductNode,
    PlaceProductTaxEnum,
    WinterStorageProductNode,
)

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


CREATE_WINTER_STORAGE_PRODUCT_MUTATION = """
mutation CREATE_WINTER_STORAGE_PRODUCT($input: CreateWinterStorageProductMutationInput!) {
    createWinterStorageProduct(input: $input) {
        winterStorageProduct {
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
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
def test_create_winter_storage_product(api_client, winter_storage_area):
    variables = {
        "priceValue": str(round(random.uniform(1, 999), 2)),
        "winterStorageAreaId": to_global_id(
            WinterStorageAreaNode, winter_storage_area.id
        ),
    }

    assert WinterStorageProduct.objects.count() == 0

    executed = api_client.execute(
        CREATE_WINTER_STORAGE_PRODUCT_MUTATION, input=variables
    )

    assert WinterStorageProduct.objects.count() == 1
    assert (
        executed["data"]["createWinterStorageProduct"]["winterStorageProduct"].pop("id")
        is not None
    )

    assert executed["data"]["createWinterStorageProduct"]["winterStorageProduct"] == {
        "priceValue": variables["priceValue"],
        "priceUnit": PriceUnits.AMOUNT.name,
        "taxPercentage": PlaceProductTaxEnum.get(DEFAULT_TAX_PERCENTAGE).name,
        "winterStorageArea": {"id": variables["winterStorageAreaId"]},
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_create_winter_storage_product_not_enough_permissions(api_client):
    variables = {"priceValue": "1.00"}

    assert WinterStorageProduct.objects.count() == 0

    executed = api_client.execute(
        CREATE_WINTER_STORAGE_PRODUCT_MUTATION, input=variables
    )

    assert WinterStorageProduct.objects.count() == 0
    assert_not_enough_permissions(executed)


def test_create_winter_storage_product_no_price_value(superuser_api_client):
    variables = {
        "winterStorageAreaId": to_global_id(WinterStorageAreaNode, uuid.uuid4()),
    }

    assert WinterStorageProduct.objects.count() == 0

    executed = superuser_api_client.execute(
        CREATE_WINTER_STORAGE_PRODUCT_MUTATION, input=variables
    )

    assert WinterStorageProduct.objects.count() == 0
    assert_field_missing("priceValue", executed)


DELETE_WINTER_STORAGE_PRODUCT_MUTATION = """
mutation DELETE_WINTER_STORAGE_PRODUCT($input: DeleteWinterStorageProductMutationInput!) {
    deleteWinterStorageProduct(input: $input) {
        clientMutationId
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
def test_delete_winter_storage_product(api_client, winter_storage_product):
    variables = {
        "id": to_global_id(WinterStorageProductNode, winter_storage_product.id)
    }
    assert WinterStorageProduct.objects.count() == 1

    api_client.execute(DELETE_WINTER_STORAGE_PRODUCT_MUTATION, input=variables)

    assert WinterStorageProduct.objects.count() == 0


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_delete_winter_storage_product_not_enough_permissions(
    api_client, winter_storage_product
):
    variables = {
        "id": to_global_id(WinterStorageProductNode, winter_storage_product.id)
    }
    assert WinterStorageProduct.objects.count() == 1

    executed = api_client.execute(
        DELETE_WINTER_STORAGE_PRODUCT_MUTATION, input=variables
    )

    assert WinterStorageProduct.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_delete_winter_storage_product_does_not_exist(superuser_api_client):
    variables = {"id": to_global_id(WinterStorageProductNode, uuid.uuid4())}

    executed = superuser_api_client.execute(
        DELETE_WINTER_STORAGE_PRODUCT_MUTATION, input=variables
    )

    assert_doesnt_exist("WinterStorageProduct", executed)


UPDATE_WINTER_STORAGE_PRODUCT_MUTATION = """
mutation UPDATE_WINTER_STORAGE_PRODUCT($input: UpdateWinterStorageProductMutationInput!) {
    updateWinterStorageProduct(input: $input) {
        winterStorageProduct {
            id
            priceValue
            priceUnit
            winterStorageArea {
                id
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
def test_update_winter_storage_product(
    api_client, winter_storage_product, winter_storage_area
):
    variables = {
        "id": to_global_id(WinterStorageProductNode, winter_storage_product.id),
        "priceValue": str(round(random.uniform(1, 999), 2)),
        "winterStorageAreaId": to_global_id(
            WinterStorageAreaNode, winter_storage_area.id
        ),
    }

    assert WinterStorageProduct.objects.count() == 1

    executed = api_client.execute(
        UPDATE_WINTER_STORAGE_PRODUCT_MUTATION, input=variables
    )

    assert WinterStorageProduct.objects.count() == 1

    assert executed["data"]["updateWinterStorageProduct"]["winterStorageProduct"] == {
        "id": variables["id"],
        "priceValue": variables["priceValue"],
        "priceUnit": PriceUnits.AMOUNT.name,
        "winterStorageArea": {"id": variables["winterStorageAreaId"]},
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_update_winter_storage_product_not_enough_permissions(api_client):
    variables = {
        "id": to_global_id(WinterStorageProductNode, uuid.uuid4()),
    }
    executed = api_client.execute(
        UPDATE_WINTER_STORAGE_PRODUCT_MUTATION, input=variables
    )

    assert_not_enough_permissions(executed)


def test_update_winter_storage_product_does_not_exist(superuser_api_client):
    variables = {
        "id": to_global_id(WinterStorageProductNode, uuid.uuid4()),
    }
    executed = superuser_api_client.execute(
        UPDATE_WINTER_STORAGE_PRODUCT_MUTATION, input=variables
    )

    assert_doesnt_exist("WinterStorageProduct", executed)


CREATE_ADDITIONAL_PRODUCT_MUTATION = """
mutation CREATE_ADDITIONAL_PRODUCT($input: CreateAdditionalProductMutationInput!) {
    createAdditionalProduct(input: $input) {
        additionalProduct {
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
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
def test_create_additional_product(api_client):
    service = random.choice(list(ProductServiceType))
    period = (
        PeriodType.SEASON
        if service.is_fixed_service()
        else random.choice(list(PeriodType))
    )
    tax_percentage = AdditionalProductTaxEnum.get(
        (
            DEFAULT_TAX_PERCENTAGE
            if service.is_fixed_service()
            else random.choice(ADDITIONAL_PRODUCT_TAX_PERCENTAGES)
        )
    )
    product_type = (
        AdditionalProductType.FIXED_SERVICE
        if service.is_fixed_service()
        else AdditionalProductType.OPTIONAL_SERVICE
    )
    variables = {
        "service": service.name,
        "period": period.name,
        "priceValue": str(round(random.uniform(1, 999), 2)),
        "priceUnit": random.choice(list(PriceUnits)).name,
        "taxPercentage": tax_percentage.name,
    }

    AdditionalProduct.objects.count() == 0

    executed = api_client.execute(CREATE_ADDITIONAL_PRODUCT_MUTATION, input=variables)

    AdditionalProduct.objects.count() == 1

    assert (
        executed["data"]["createAdditionalProduct"]["additionalProduct"].pop("id")
        is not None
    )

    assert executed["data"]["createAdditionalProduct"]["additionalProduct"] == {
        "service": variables["service"],
        "period": variables["period"],
        "priceValue": variables["priceValue"],
        "priceUnit": variables["priceUnit"],
        "taxPercentage": variables["taxPercentage"],
        "productType": product_type.name,
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_create_additional_product_not_enough_permissions(api_client):
    variables = {
        "service": random.choice(list(ProductServiceType)).name,
        "period": random.choice(list(PeriodType)).name,
        "priceValue": "1.00",
    }

    executed = api_client.execute(CREATE_ADDITIONAL_PRODUCT_MUTATION, input=variables)

    assert_not_enough_permissions(executed)


DELETE_ADDITIONAL_PRODUCT_MUTATION = """
mutation DELETE_ADDITIONAL_PRODUCT($input: DeleteAdditionalProductMutationInput!) {
    deleteAdditionalProduct(input: $input) {
        clientMutationId
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
def test_delete_additional_product(api_client, additional_product):
    variables = {"id": to_global_id(AdditionalProductNode, additional_product.id)}
    assert AdditionalProduct.objects.count() == 1

    api_client.execute(DELETE_ADDITIONAL_PRODUCT_MUTATION, input=variables)

    assert AdditionalProduct.objects.count() == 0


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_delete_additional_product_not_enough_permissions(
    api_client, additional_product
):
    variables = {"id": to_global_id(AdditionalProductNode, additional_product.id)}
    assert AdditionalProduct.objects.count() == 1

    executed = api_client.execute(DELETE_ADDITIONAL_PRODUCT_MUTATION, input=variables)

    assert AdditionalProduct.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_delete_additional_product_does_not_exist(superuser_api_client):
    variables = {"id": to_global_id(AdditionalProductNode, uuid.uuid4())}

    executed = superuser_api_client.execute(
        DELETE_ADDITIONAL_PRODUCT_MUTATION, input=variables
    )

    assert_doesnt_exist("AdditionalProduct", executed)


UPDATE_ADDITIONAL_PRODUCT_MUTATION = """
mutation UPDATE_ADDITIONAL_PRODUCT($input: UpdateAdditionalProductMutationInput!) {
    updateAdditionalProduct(input: $input) {
        additionalProduct {
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
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
def test_update_additional_product(api_client, additional_product):
    product_global_id = to_global_id(AdditionalProductNode, additional_product.id)
    service = random.choice(list(ProductServiceType))
    period = (
        PeriodType.SEASON
        if service.is_fixed_service()
        else random.choice(list(PeriodType))
    )
    tax_percentage = AdditionalProductTaxEnum.get(
        (
            DEFAULT_TAX_PERCENTAGE
            if service.is_fixed_service()
            else random.choice(ADDITIONAL_PRODUCT_TAX_PERCENTAGES)
        )
    )
    product_type = (
        AdditionalProductType.FIXED_SERVICE
        if service.is_fixed_service()
        else AdditionalProductType.OPTIONAL_SERVICE
    )
    variables = {
        "id": product_global_id,
        "service": service.name,
        "period": period.name,
        "priceValue": str(round(random.uniform(1, 999), 2)),
        "priceUnit": random.choice(list(PriceUnits)).name,
        "taxPercentage": tax_percentage.name,
    }

    AdditionalProduct.objects.count() == 1

    executed = api_client.execute(UPDATE_ADDITIONAL_PRODUCT_MUTATION, input=variables)

    AdditionalProduct.objects.count() == 1

    assert executed["data"]["updateAdditionalProduct"]["additionalProduct"] == {
        "id": variables["id"],
        "service": variables["service"],
        "period": variables["period"],
        "priceValue": variables["priceValue"],
        "priceUnit": variables["priceUnit"],
        "taxPercentage": variables["taxPercentage"],
        "productType": product_type.name,
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_update_additional_product_not_enough_permissions(
    api_client, additional_product
):
    variables = {
        "id": to_global_id(AdditionalProductNode, additional_product.id),
    }

    executed = api_client.execute(UPDATE_ADDITIONAL_PRODUCT_MUTATION, input=variables)

    assert_not_enough_permissions(executed)
