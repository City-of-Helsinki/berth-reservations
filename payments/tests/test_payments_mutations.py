import random
import uuid

import pytest
from dateutil.utils import today
from freezegun import freeze_time

from berth_reservations.tests.utils import (
    assert_doesnt_exist,
    assert_field_missing,
    assert_not_enough_permissions,
)
from customers.schema import ProfileNode
from leases.models import BerthLease
from leases.schema import BerthLeaseNode
from resources.schema import HarborNode, WinterStorageAreaNode
from utils.relay import to_global_id

from ..enums import (
    AdditionalProductType,
    OrderStatus,
    PeriodType,
    PriceUnits,
    ProductServiceType,
)
from ..models import (
    BerthProduct,
    DEFAULT_TAX_PERCENTAGE,
    Order,
    OrderLine,
    WinterStorageProduct,
)
from ..schema.types import (
    ADDITIONAL_PRODUCT_TAX_PERCENTAGES,
    AdditionalProduct,
    AdditionalProductNode,
    AdditionalProductTaxEnum,
    BerthPriceGroupNode,
    BerthProductNode,
    OrderLineNode,
    OrderNode,
    PlaceProductTaxEnum,
    WinterStorageProductNode,
)
from ..utils import (
    calculate_product_partial_month_price,
    calculate_product_partial_season_price,
    calculate_product_partial_year_price,
    calculate_product_percentage_price,
    convert_aftertax_to_pretax,
    round_price,
)
from .factories import OrderFactory

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


CREATE_ORDER_MUTATION = """
mutation CREATE_ORDER($input: CreateOrderMutationInput!) {
    createOrder(input: $input) {
        order {
            id
            price
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
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
def test_create_order_berth_product(api_client, berth_product, berth_lease):
    customer_id = to_global_id(ProfileNode, berth_lease.customer.id)
    product_id = to_global_id(BerthProductNode, berth_product.id)
    lease_id = to_global_id(BerthLeaseNode, berth_lease.id)

    variables = {
        "customerId": customer_id,
        "productId": product_id,
        "leaseId": lease_id,
    }

    assert Order.objects.count() == 0

    executed = api_client.execute(CREATE_ORDER_MUTATION, input=variables)

    assert Order.objects.count() == 1
    assert executed["data"]["createOrder"]["order"].pop("id") is not None

    assert executed["data"]["createOrder"]["order"] == {
        "price": str(berth_product.price_value),
        "taxPercentage": str(berth_product.tax_percentage),
        "customer": {"id": variables["customerId"]},
        "product": {"id": variables["productId"]},
        "lease": {"id": variables["leaseId"]},
    }


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
def test_create_order_winter_storage_product(
    api_client, winter_storage_product, customer_profile
):
    customer_id = to_global_id(ProfileNode, customer_profile.id)
    product_id = to_global_id(WinterStorageProductNode, winter_storage_product.id)

    variables = {
        "customerId": customer_id,
        "productId": product_id,
    }

    assert Order.objects.count() == 0

    executed = api_client.execute(CREATE_ORDER_MUTATION, input=variables)

    assert Order.objects.count() == 1
    assert executed["data"]["createOrder"]["order"].pop("id") is not None

    assert executed["data"]["createOrder"]["order"] == {
        "price": str(winter_storage_product.price_value),
        "taxPercentage": str(winter_storage_product.tax_percentage),
        "customer": {"id": variables["customerId"]},
        "product": {"id": variables["productId"]},
        "lease": None,
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_create_order_not_enough_permissions(api_client):
    variables = {
        "customerId": to_global_id(ProfileNode, uuid.uuid4()),
    }

    assert Order.objects.count() == 0

    executed = api_client.execute(CREATE_ORDER_MUTATION, input=variables)

    assert Order.objects.count() == 0
    assert_not_enough_permissions(executed)


def test_create_order_profile_does_not_exist(superuser_api_client):
    variables = {
        "customerId": to_global_id(ProfileNode, uuid.uuid4()),
    }

    assert Order.objects.count() == 0

    executed = superuser_api_client.execute(CREATE_ORDER_MUTATION, input=variables)

    assert Order.objects.count() == 0
    assert_doesnt_exist("CustomerProfile", executed)


UPDATE_ORDER_MUTATION = """
mutation UPDATE_ORDER($input: UpdateOrderMutationInput!) {
    updateOrder(input: $input) {
        order {
            id
            comment
            price
            taxPercentage
            dueDate
            status
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
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_update_order_berth_product(api_client, berth_product, berth_lease):
    order = OrderFactory(
        product=berth_product, lease=berth_lease, customer=berth_lease.customer
    )
    global_id = to_global_id(OrderNode, order.id)

    variables = {
        "id": global_id,
        "comment": "foobar",
        "dueDate": today(),
        "status": random.choice(list(OrderStatus)).name,
    }

    assert Order.objects.count() == 1

    executed = api_client.execute(UPDATE_ORDER_MUTATION, input=variables)

    assert Order.objects.count() == 1

    assert executed["data"]["updateOrder"]["order"] == {
        "id": variables["id"],
        "comment": variables["comment"],
        "price": str(berth_product.price_value),
        "taxPercentage": str(berth_product.tax_percentage),
        "dueDate": str(variables["dueDate"].date()),
        "status": variables["status"],
        "customer": {"id": to_global_id(ProfileNode, order.customer.id)},
        "product": {"id": to_global_id(BerthProductNode, order.product.id)},
        "lease": {"id": to_global_id(BerthLeaseNode, berth_lease.id)},
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_update_order_not_enough_permissions(api_client):
    variables = {
        "id": to_global_id(OrderNode, uuid.uuid4()),
    }

    assert Order.objects.count() == 0

    executed = api_client.execute(UPDATE_ORDER_MUTATION, input=variables)

    assert Order.objects.count() == 0
    assert_not_enough_permissions(executed)


def test_update_order_does_not_exist(superuser_api_client):
    variables = {
        "id": to_global_id(OrderNode, uuid.uuid4()),
    }
    executed = superuser_api_client.execute(UPDATE_ORDER_MUTATION, input=variables)

    assert_doesnt_exist("Order", executed)


def test_update_order_lease_does_not_exist(superuser_api_client, order):
    variables = {
        "id": to_global_id(OrderNode, order.id),
        "leaseId": to_global_id(BerthLeaseNode, uuid.uuid4()),
    }
    executed = superuser_api_client.execute(UPDATE_ORDER_MUTATION, input=variables)

    assert_doesnt_exist("BerthLease", executed)


DELETE_ORDER_MUTATION = """
mutation DELETE_ORDER($input: DeleteOrderMutationInput!) {
    deleteOrder(input: $input) {
        clientMutationId
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
def test_delete_order(api_client, order):
    variables = {"id": to_global_id(OrderNode, order.id)}
    assert Order.objects.count() == 1

    api_client.execute(DELETE_ORDER_MUTATION, input=variables)

    assert Order.objects.count() == 0


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_delete_order_not_enough_permissions(api_client, order):
    variables = {"id": to_global_id(OrderNode, order.id)}
    assert Order.objects.count() == 1

    executed = api_client.execute(DELETE_ORDER_MUTATION, input=variables)

    assert Order.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_delete_order_does_not_exist(superuser_api_client):
    variables = {"id": to_global_id(OrderNode, uuid.uuid4())}

    executed = superuser_api_client.execute(DELETE_ORDER_MUTATION, input=variables)

    assert_doesnt_exist("Order", executed)


CREATE_ORDER_LINE_MUTATION = """
mutation CREATE_ORDER_LINE($input: CreateOrderLineMutationInput!) {
    createOrderLine(input: $input) {
        orderLine {
            id
            price
            taxPercentage
            pretaxPrice
            product {
                id
                priceValue
                priceUnit
            }
        }
        order {
            id
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
def test_create_order_line(api_client, order, additional_product):
    order_id = to_global_id(OrderNode, order.id)
    product_id = to_global_id(AdditionalProductNode, additional_product.id)

    variables = {
        "orderId": order_id,
        "productId": product_id,
    }

    assert OrderLine.objects.count() == 0

    executed = api_client.execute(CREATE_ORDER_LINE_MUTATION, input=variables)

    assert OrderLine.objects.count() == 1

    expected_price = additional_product.price_value
    if additional_product.price_unit == PriceUnits.PERCENTAGE:
        expected_price = calculate_product_percentage_price(
            order.price, additional_product.price_value
        )

    if additional_product.period == PeriodType.MONTH:
        expected_price = calculate_product_partial_month_price(
            expected_price, order.lease.start_date, order.lease.end_date
        )
    elif additional_product.period == PeriodType.SEASON:
        expected_price = calculate_product_partial_season_price(
            expected_price,
            order.lease.start_date,
            order.lease.end_date,
            summer_season=isinstance(order.lease, BerthLease),
        )
    elif additional_product.period == PeriodType.YEAR:
        expected_price = calculate_product_partial_year_price(
            expected_price, order.lease.start_date, order.lease.end_date
        )

    assert executed["data"]["createOrderLine"]["orderLine"].pop("id") is not None
    assert executed["data"]["createOrderLine"] == {
        "orderLine": {
            "price": str(expected_price),
            "taxPercentage": str(round_price(additional_product.tax_percentage)),
            "pretaxPrice": str(
                convert_aftertax_to_pretax(
                    expected_price, additional_product.tax_percentage,
                )
            ),
            "product": {
                "id": to_global_id(AdditionalProductNode, additional_product.id),
                "priceValue": str(additional_product.price_value),
                "priceUnit": additional_product.price_unit.name,
            },
        },
        "order": {"id": order_id},
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_create_order_line_not_enough_permissions(api_client):
    variables = {
        "orderId": to_global_id(OrderNode, uuid.uuid4()),
        "productId": to_global_id(ProfileNode, uuid.uuid4()),
    }

    assert OrderLine.objects.count() == 0

    executed = api_client.execute(CREATE_ORDER_LINE_MUTATION, input=variables)

    assert OrderLine.objects.count() == 0
    assert_not_enough_permissions(executed)


def test_create_order_line_order_does_not_exist(
    superuser_api_client, additional_product
):
    variables = {
        "orderId": to_global_id(OrderNode, uuid.uuid4()),
        "productId": to_global_id(ProfileNode, additional_product.id),
    }

    assert OrderLine.objects.count() == 0

    executed = superuser_api_client.execute(CREATE_ORDER_LINE_MUTATION, input=variables)

    assert OrderLine.objects.count() == 0
    assert_doesnt_exist("Order", executed)


def test_create_order_line_product_does_not_exist(superuser_api_client, order):
    variables = {
        "orderId": to_global_id(OrderNode, order.id),
        "productId": to_global_id(AdditionalProductNode, uuid.uuid4()),
    }

    assert OrderLine.objects.count() == 0

    executed = superuser_api_client.execute(CREATE_ORDER_LINE_MUTATION, input=variables)

    assert OrderLine.objects.count() == 0
    assert_doesnt_exist("AdditionalProduct", executed)


UPDATE_ORDER_LINE_MUTATION = """
mutation UPDATE_ORDER_LINE($input: UpdateOrderLineMutationInput!) {
    updateOrderLine(input: $input) {
        orderLine {
            id
            quantity
            product {
                id
            }
        }
        order {
            id
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
def test_update_order_line(api_client, order_line):
    order_line_id = to_global_id(OrderLineNode, order_line.id)
    product_id = to_global_id(AdditionalProductNode, order_line.product.id)

    variables = {
        "id": order_line_id,
        "quantity": random.randint(1, 5),
    }

    assert OrderLine.objects.count() == 1

    executed = api_client.execute(UPDATE_ORDER_LINE_MUTATION, input=variables)

    assert OrderLine.objects.count() == 1

    assert executed["data"]["updateOrderLine"]["orderLine"] == {
        "id": order_line_id,
        "quantity": variables["quantity"],
        "product": {"id": product_id},
    }
    assert executed["data"]["updateOrderLine"]["order"]["id"] == to_global_id(
        OrderNode, order_line.order.id
    )


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_update_order_line_not_enough_permissions(api_client):
    variables = {
        "id": to_global_id(OrderNode, uuid.uuid4()),
    }

    executed = api_client.execute(UPDATE_ORDER_LINE_MUTATION, input=variables)

    assert_not_enough_permissions(executed)


def test_update_order_line_does_not_exist(superuser_api_client):
    variables = {
        "id": to_global_id(OrderLineNode, uuid.uuid4()),
    }
    executed = superuser_api_client.execute(UPDATE_ORDER_LINE_MUTATION, input=variables)

    assert_doesnt_exist("OrderLine", executed)


DELETE_ORDER_LINE_MUTATION = """
mutation DELETE_ORDER_LINE($input: DeleteOrderLineMutationInput!) {
    deleteOrderLine(input: $input) {
        clientMutationId
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
def test_delete_order_line(api_client, order_line):
    variables = {"id": to_global_id(OrderLineNode, order_line.id)}
    assert OrderLine.objects.count() == 1

    api_client.execute(DELETE_ORDER_LINE_MUTATION, input=variables)

    assert OrderLine.objects.count() == 0


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_delete_order_line_not_enough_permissions(api_client, order_line):
    variables = {"id": to_global_id(OrderLineNode, order_line.id)}
    assert OrderLine.objects.count() == 1

    executed = api_client.execute(DELETE_ORDER_LINE_MUTATION, input=variables)

    assert OrderLine.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_delete_order_line_does_not_exist(superuser_api_client):
    variables = {"id": to_global_id(OrderLineNode, uuid.uuid4())}

    executed = superuser_api_client.execute(DELETE_ORDER_LINE_MUTATION, input=variables)

    assert_doesnt_exist("OrderLine", executed)
