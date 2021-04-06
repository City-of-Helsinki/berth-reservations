import datetime
import random
import uuid
from unittest import mock

import pytest
from babel.dates import format_date
from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from django.core import mail
from django.utils.timezone import now
from freezegun import freeze_time

from applications.enums import ApplicationStatus
from berth_reservations.tests.utils import (
    assert_doesnt_exist,
    assert_field_missing,
    assert_in_errors,
    assert_not_enough_permissions,
)
from customers.schema import ProfileNode
from leases.enums import LeaseStatus
from leases.schema import BerthLeaseNode, WinterStorageLeaseNode
from leases.tests.factories import BerthLeaseFactory
from leases.utils import calculate_season_start_date
from resources.schema import WinterStorageAreaNode
from utils.numbers import rounded
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
    OrderToken,
    WinterStorageProduct,
)
from ..schema.types import (
    ADDITIONAL_PRODUCT_TAX_PERCENTAGES,
    AdditionalProduct,
    AdditionalProductNode,
    AdditionalProductTaxEnum,
    AdditionalProductTypeEnum,
    BerthProductNode,
    OrderLineNode,
    OrderNode,
    OrderStatusEnum,
    PeriodTypeEnum,
    PlaceProductTaxEnum,
    PriceUnitsEnum,
    ProductServiceTypeEnum,
    WinterStorageProductNode,
)
from ..utils import (
    calculate_product_partial_month_price,
    calculate_product_partial_year_price,
    calculate_product_percentage_price,
    convert_aftertax_to_pretax,
    generate_order_number,
)
from .conftest import mocked_response_create
from .factories import OrderFactory
from .utils import random_price

CREATE_BERTH_PRODUCT_MUTATION = """
mutation CREATE_BERTH_PRODUCT($input: CreateBerthProductMutationInput!) {
    createBerthProduct(input: $input) {
        berthProduct {
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
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
def test_create_berth_product(api_client, harbor):
    min_width = rounded(random.uniform(0, 5), round_to_nearest=0.05, as_string=True)
    variables = {
        "minWidth": min_width,
        "maxWidth": rounded(
            random.uniform(float(min_width), 6), round_to_nearest=0.05, as_string=True
        ),
        "tier1Price": str(random_price()),
        "tier2Price": str(random_price()),
        "tier3Price": str(random_price()),
    }

    assert BerthProduct.objects.count() == 0

    executed = api_client.execute(CREATE_BERTH_PRODUCT_MUTATION, input=variables)

    assert BerthProduct.objects.count() == 1
    assert executed["data"]["createBerthProduct"]["berthProduct"].pop("id") is not None

    assert executed["data"]["createBerthProduct"]["berthProduct"] == {
        "minWidth": str(variables["minWidth"]),
        "maxWidth": str(variables["maxWidth"]),
        "tier1Price": variables["tier1Price"],
        "tier2Price": variables["tier2Price"],
        "tier3Price": variables["tier3Price"],
        "priceUnit": PriceUnitsEnum.AMOUNT.name,
        "taxPercentage": PlaceProductTaxEnum.get(DEFAULT_TAX_PERCENTAGE).name,
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_create_berth_product_not_enough_permissions(api_client):
    variables = {
        "minWidth": rounded(random.uniform(0, 5), round_to_nearest=0.05),
        "maxWidth": rounded(random.uniform(0, 6), round_to_nearest=0.05),
        "tier1Price": str(random_price()),
        "tier2Price": str(random_price()),
        "tier3Price": str(random_price()),
    }

    assert BerthProduct.objects.count() == 0

    executed = api_client.execute(CREATE_BERTH_PRODUCT_MUTATION, input=variables)

    assert BerthProduct.objects.count() == 0
    assert_not_enough_permissions(executed)


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
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
def test_update_berth_product(api_client, berth_product, harbor):
    variables = {
        "id": to_global_id(BerthProductNode, berth_product.id),
        "minWidth": rounded(
            random.uniform(0, 5), round_to_nearest=0.05, as_string=True
        ),
        "maxWidth": rounded(
            random.uniform(0, 6), round_to_nearest=0.05, as_string=True
        ),
        "tier1Price": str(random_price()),
        "tier2Price": str(random_price()),
        "tier3Price": str(random_price()),
    }

    assert BerthProduct.objects.count() == 1

    executed = api_client.execute(UPDATE_BERTH_PRODUCT_MUTATION, input=variables)

    assert BerthProduct.objects.count() == 1

    assert executed["data"]["updateBerthProduct"]["berthProduct"] == {
        "id": variables["id"],
        "minWidth": str(variables["minWidth"]),
        "maxWidth": str(variables["maxWidth"]),
        "tier1Price": variables["tier1Price"],
        "tier2Price": variables["tier2Price"],
        "tier3Price": variables["tier3Price"],
        "priceUnit": PriceUnitsEnum.AMOUNT.name,
        "taxPercentage": PlaceProductTaxEnum.get(DEFAULT_TAX_PERCENTAGE).name,
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
        "priceValue": str(random_price()),
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
        "priceUnit": PriceUnitsEnum.AMOUNT.name,
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
        "priceUnit": PriceUnitsEnum.AMOUNT.name,
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
    service = ProductServiceTypeEnum.get(random.choice(ProductServiceType.values))
    period = PeriodTypeEnum.get(
        PeriodType.SEASON
        if service in ProductServiceType.FIXED_SERVICES()
        else random.choice(PeriodType.values)
    )
    tax_percentage = AdditionalProductTaxEnum.get(
        DEFAULT_TAX_PERCENTAGE
        if service in ProductServiceType.FIXED_SERVICES()
        else random.choice(ADDITIONAL_PRODUCT_TAX_PERCENTAGES)
    )
    product_type = AdditionalProductTypeEnum.get(
        AdditionalProductType.FIXED_SERVICE
        if service in ProductServiceType.FIXED_SERVICES()
        else AdditionalProductType.OPTIONAL_SERVICE
    )
    variables = {
        "service": service.name,
        "period": period.name,
        "priceValue": str(random_price()),
        "priceUnit": PriceUnitsEnum.get(random.choice(PriceUnits.values)).name,
        "taxPercentage": tax_percentage.name,
    }

    assert AdditionalProduct.objects.count() == 0

    executed = api_client.execute(CREATE_ADDITIONAL_PRODUCT_MUTATION, input=variables)

    assert AdditionalProduct.objects.count() == 1

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
    service = ProductServiceTypeEnum.get(random.choice(ProductServiceType.values))
    period = PeriodTypeEnum.get(random.choice(PeriodType.values))
    variables = {
        "service": service.name,
        "period": period.name,
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
    service = ProductServiceTypeEnum.get(random.choice(ProductServiceType.values))
    period = PeriodTypeEnum.get(
        PeriodType.SEASON
        if service in ProductServiceType.FIXED_SERVICES()
        else random.choice(PeriodType.values)
    )
    tax_percentage = AdditionalProductTaxEnum.get(
        DEFAULT_TAX_PERCENTAGE
        if service in ProductServiceType.FIXED_SERVICES()
        else random.choice(ADDITIONAL_PRODUCT_TAX_PERCENTAGES)
    )
    product_type = AdditionalProductTypeEnum.get(
        AdditionalProductType.FIXED_SERVICE
        if service in ProductServiceType.FIXED_SERVICES()
        else AdditionalProductType.OPTIONAL_SERVICE
    )
    variables = {
        "id": product_global_id,
        "service": service.name,
        "period": period.name,
        "priceValue": str(random_price()),
        "priceUnit": PriceUnitsEnum.get(random.choice(PriceUnits.values)).name,
        "taxPercentage": tax_percentage.name,
    }

    assert AdditionalProduct.objects.count() == 1

    executed = api_client.execute(UPDATE_ADDITIONAL_PRODUCT_MUTATION, input=variables)

    assert AdditionalProduct.objects.count() == 1

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
# Freezing time to avoid season price miscalculation
@freeze_time("2020-01-01T08:00:00Z")
def test_create_order_berth_product(api_client, berth_product):
    berth_lease = BerthLeaseFactory(start_date=calculate_season_start_date())
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
        "price": str(berth_product.price_for_tier(berth_lease.berth.pier.price_tier)),
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


@pytest.mark.parametrize("lease_type", ["berth", "winter"])
def test_create_order_lease_does_not_exist(
    superuser_api_client, customer_profile, lease_type
):
    lease_id = to_global_id(
        BerthLeaseNode if lease_type == "berth" else WinterStorageLeaseNode,
        uuid.uuid4(),
    )
    variables = {
        "customerId": to_global_id(ProfileNode, customer_profile.id),
        "leaseId": lease_id,
    }

    assert Order.objects.count() == 0

    executed = superuser_api_client.execute(CREATE_ORDER_MUTATION, input=variables)

    assert Order.objects.count() == 0
    assert_in_errors("Lease with the given ID does not exist", executed)


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
@pytest.mark.parametrize(
    "status_choice",
    [
        OrderStatus.PAID,
        OrderStatus.PAID_MANUALLY,
        OrderStatus.EXPIRED,
        OrderStatus.REJECTED,
        OrderStatus.ERROR,
    ],
)
@freeze_time("2020-01-01T08:00:00Z")
def test_update_order_berth_product(
    api_client, status_choice, berth_product, berth_lease
):
    order = OrderFactory(
        product=berth_product,
        lease=berth_lease,
        customer=berth_lease.customer,
        status=OrderStatus.OFFERED,
    )

    global_id = to_global_id(OrderNode, order.id)

    # only valid state transitions
    variables = {
        "id": global_id,
        "comment": "foobar",
        "dueDate": today(),
        "status": OrderStatusEnum.get(status_choice.value).name,
    }

    assert Order.objects.count() == 1

    executed = api_client.execute(UPDATE_ORDER_MUTATION, input=variables)
    assert Order.objects.count() == 1

    assert executed["data"]["updateOrder"]["order"] == {
        "id": variables["id"],
        "comment": variables["comment"],
        "price": str(berth_product.price_for_tier(berth_lease.berth.pier.price_tier)),
        "taxPercentage": str(berth_product.tax_percentage),
        "dueDate": str(variables["dueDate"].date()),
        "status": variables["status"],
        "customer": {"id": to_global_id(ProfileNode, order.customer.id)},
        "product": {"id": to_global_id(BerthProductNode, order.product.id)},
        "lease": {"id": to_global_id(BerthLeaseNode, berth_lease.id)},
    }


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
@pytest.mark.parametrize(
    "initial_status", [OrderStatus.DRAFTED, OrderStatus.OFFERED, OrderStatus.ERROR]
)
@freeze_time("2020-01-01T08:00:00Z")
def test_set_order_status_to_paid_manually(
    api_client, initial_status, berth_product, berth_lease
):
    order = OrderFactory(
        product=berth_product,
        lease=berth_lease,
        customer=berth_lease.customer,
        status=initial_status,
    )
    assert order.status == initial_status
    global_id = to_global_id(OrderNode, order.id)
    variables = {
        "id": global_id,
        "status": OrderStatusEnum.get(OrderStatus.PAID_MANUALLY).name,
    }

    assert Order.objects.count() == 1

    executed = api_client.execute(UPDATE_ORDER_MUTATION, input=variables)

    assert Order.objects.count() == 1

    assert executed["data"]["updateOrder"]["order"] == {
        "id": variables["id"],
        "comment": order.comment,
        "price": str(berth_product.price_for_tier(berth_lease.berth.pier.price_tier)),
        "taxPercentage": str(berth_product.tax_percentage),
        "status": OrderStatus.PAID_MANUALLY.name,
        "dueDate": str(order.due_date),
        "customer": {"id": to_global_id(ProfileNode, order.customer.id)},
        "product": {"id": to_global_id(BerthProductNode, order.product.id)},
        "lease": {"id": to_global_id(BerthLeaseNode, berth_lease.id)},
    }
    order.refresh_from_db()
    order.lease.refresh_from_db()
    assert order.log_entries.count() == 1
    log_entry = order.log_entries.first()
    assert log_entry.to_status == OrderStatus.PAID_MANUALLY
    assert "Manually updated by admin" in log_entry.comment
    assert order.lease.status == LeaseStatus.PAID


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
@pytest.mark.parametrize("initial_status", [OrderStatus.OFFERED, OrderStatus.ERROR])
@freeze_time("2020-01-01T08:00:00Z")
def test_set_order_status_to_cancelled(
    api_client, initial_status, berth_product, berth_lease
):
    # note: test_cancel_order tests the case where customer rejects the order(and berth).
    order = OrderFactory(
        product=berth_product,
        lease=berth_lease,
        customer=berth_lease.customer,
        status=initial_status,
    )
    lease_initial_status = berth_lease.status
    assert order.status == initial_status
    global_id = to_global_id(OrderNode, order.id)
    variables = {
        "id": global_id,
        "status": OrderStatusEnum.get(OrderStatus.CANCELLED).name,
    }

    assert Order.objects.count() == 1

    executed = api_client.execute(UPDATE_ORDER_MUTATION, input=variables)

    assert Order.objects.count() == 1

    assert executed["data"]["updateOrder"]["order"] == {
        "id": variables["id"],
        "comment": order.comment,
        "status": OrderStatus.CANCELLED.name,
        "price": str(berth_product.price_for_tier(berth_lease.berth.pier.price_tier)),
        "taxPercentage": str(berth_product.tax_percentage),
        "dueDate": str(order.due_date),
        "customer": {"id": to_global_id(ProfileNode, order.customer.id)},
        "product": {"id": to_global_id(BerthProductNode, order.product.id)},
        "lease": {"id": to_global_id(BerthLeaseNode, berth_lease.id)},
    }
    order.refresh_from_db()
    order.lease.refresh_from_db()
    assert order.lease.status == lease_initial_status
    assert order.log_entries.count() == 1
    log_entry = order.log_entries.first()
    assert log_entry.to_status == OrderStatus.CANCELLED
    assert "Manually updated by admin" in log_entry.comment


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


@pytest.mark.parametrize("lease_type", ["berth", "winter"])
def test_update_order_lease_does_not_exist(superuser_api_client, order, lease_type):
    lease_id = to_global_id(
        BerthLeaseNode if lease_type == "berth" else WinterStorageLeaseNode,
        uuid.uuid4(),
    )
    variables = {
        "id": to_global_id(OrderNode, order.id),
        "leaseId": lease_id,
    }
    executed = superuser_api_client.execute(UPDATE_ORDER_MUTATION, input=variables)

    assert_in_errors("Lease with the given ID does not exist", executed)


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
    elif additional_product.period == PeriodType.YEAR:
        expected_price = calculate_product_partial_year_price(
            expected_price, order.lease.start_date, order.lease.end_date
        )
    # Season price is the same

    assert executed["data"]["createOrderLine"]["orderLine"].pop("id") is not None
    assert executed["data"]["createOrderLine"] == {
        "orderLine": {
            "price": str(expected_price),
            "taxPercentage": rounded(
                additional_product.tax_percentage,
                decimals=2,
                round_to_nearest=0.05,
                as_string=True,
            ),
            "pretaxPrice": str(
                convert_aftertax_to_pretax(
                    expected_price, additional_product.tax_percentage,
                )
            ),
            "product": {
                "id": to_global_id(AdditionalProductNode, additional_product.id),
                "priceValue": str(additional_product.price_value),
                "priceUnit": PriceUnitsEnum.get(additional_product.price_unit).name,
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


CONFIRM_PAYMENT_MUTATION = """
mutation CONFIRM_PAYMENT_MUTATION($input: ConfirmPaymentMutationInput!) {
    confirmPayment(input: $input) {
        url
    }
}
"""


@freeze_time("2020-01-31T08:00:00Z")
@pytest.mark.parametrize(
    "order", ["berth_order", "winter_storage_order"], indirect=True,
)
@pytest.mark.parametrize("status", [OrderStatus.OFFERED, OrderStatus.REJECTED])
def test_confirm_payment(old_schema_api_client, order: Order, status):
    order.status = status
    order.save()
    variables = {"orderNumber": order.order_number}

    with mock.patch(
        "payments.providers.bambora_payform.requests.post",
        side_effect=mocked_response_create,
    ):
        executed = old_schema_api_client.execute(
            CONFIRM_PAYMENT_MUTATION, input=variables
        )

    assert "token/token123" in executed["data"]["confirmPayment"]["url"]


def test_confirm_payment_does_not_exist(old_schema_api_client):
    variables = {"orderNumber": generate_order_number()}

    with mock.patch(
        "payments.providers.bambora_payform.requests.post",
        side_effect=mocked_response_create,
    ):
        executed = old_schema_api_client.execute(
            CONFIRM_PAYMENT_MUTATION, input=variables
        )

    assert_doesnt_exist("Order", executed)


@pytest.mark.parametrize(
    "status", [OrderStatus.EXPIRED, OrderStatus.CANCELLED, OrderStatus.PAID]
)
def test_confirm_payment_invalid_status(old_schema_api_client, status):
    order = OrderFactory(status=status)
    variables = {"orderNumber": order.order_number}

    with mock.patch(
        "payments.providers.bambora_payform.requests.post",
        side_effect=mocked_response_create,
    ) as mock_call:
        executed = old_schema_api_client.execute(
            CONFIRM_PAYMENT_MUTATION, input=variables
        )

    mock_call.assert_not_called()
    assert_in_errors("The order is not valid anymore", executed)
    assert_in_errors(status.label, executed)


@pytest.mark.parametrize(
    "order", ["berth_order", "winter_storage_order"], indirect=True,
)
def test_payment_fails_doesnt_use_empty_token(old_schema_api_client, order: Order):
    empty_token = OrderToken.objects.create(
        order=order, valid_until=now() + relativedelta(day=1)
    )

    order.status = OrderStatus.OFFERED
    order.save()
    variables = {"orderNumber": order.order_number}

    with mock.patch(
        "payments.providers.bambora_payform.requests.post",
        side_effect=mocked_response_create,
    ):
        old_schema_api_client.execute(CONFIRM_PAYMENT_MUTATION, input=variables)

    empty_token.refresh_from_db()
    assert not empty_token.is_valid
    assert OrderToken.objects.filter(order=order).count() == 2


CANCEL_ORDER_MUTATION = """
mutation CANCEL_ORDER_MUTATION($input: CancelOrderMutationInput!) {
    cancelOrder(input: $input) {
        __typename
    }
}
"""


@pytest.mark.parametrize(
    "order", ["berth_order", "winter_storage_order"], indirect=True,
)
def test_cancel_order(
    old_schema_api_client, order: Order, notification_template_order_cancelled
):
    order.status = OrderStatus.OFFERED
    order.save()
    variables = {"orderNumber": order.order_number}

    with mock.patch(
        "payments.providers.bambora_payform.requests.post",
        side_effect=mocked_response_create,
    ):
        old_schema_api_client.execute(CANCEL_ORDER_MUTATION, input=variables)

    order.refresh_from_db()
    order.lease.refresh_from_db()

    assert order.status == OrderStatus.REJECTED
    assert order.lease.status == LeaseStatus.REFUSED
    assert order.lease.application.status == ApplicationStatus.REJECTED

    assert len(mail.outbox) == 1
    assert (
        mail.outbox[0].subject == f"test order cancelled subject: {order.order_number}!"
    )
    assert (
        mail.outbox[0].body
        == f"{ order.order_number } {format_date(datetime.date.today(), locale='fi')}"
    )
    assert mail.outbox[0].to == [order.lease.application.email]

    assert mail.outbox[0].alternatives == [
        (
            f"<b>{ order.order_number } {format_date(datetime.date.today(), locale='fi')}</b>",
            "text/html",
        )
    ]


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order", "unmarked_winter_storage_order"],
    indirect=True,
)
@pytest.mark.parametrize(
    "status",
    [
        OrderStatus.REJECTED,
        OrderStatus.EXPIRED,
        OrderStatus.CANCELLED,
        OrderStatus.PAID,
    ],
)
def test_cancel_order_invalid_status(
    old_schema_api_client, order: Order, status: OrderStatus
):
    order.status = status
    order.save()
    variables = {"orderNumber": order.order_number}

    with mock.patch(
        "payments.providers.bambora_payform.requests.post",
        side_effect=mocked_response_create,
    ):
        executed = old_schema_api_client.execute(CANCEL_ORDER_MUTATION, input=variables)

    assert_in_errors(f"The order is not valid anymore: {status.label}", executed)


def test_cancel_order_does_not_exist(old_schema_api_client):
    variables = {"orderNumber": generate_order_number()}

    with mock.patch(
        "payments.providers.bambora_payform.requests.post",
        side_effect=mocked_response_create,
    ):
        executed = old_schema_api_client.execute(CANCEL_ORDER_MUTATION, input=variables)

    assert_doesnt_exist("Order", executed)


@pytest.mark.parametrize(
    "order", ["unmarked_winter_storage_order"], indirect=True,
)
def test_cancel_unmarked_order_fails(old_schema_api_client, order: Order):
    order.status = OrderStatus.OFFERED
    order.save()
    variables = {"orderNumber": order.order_number}

    with mock.patch(
        "payments.providers.bambora_payform.requests.post",
        side_effect=mocked_response_create,
    ):
        executed = old_schema_api_client.execute(CANCEL_ORDER_MUTATION, input=variables)

    assert_in_errors("Cannot cancel Unmarked winter storage order", executed)
