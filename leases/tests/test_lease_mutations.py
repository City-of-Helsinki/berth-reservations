import uuid
from random import randint

import pytest
from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from freezegun import freeze_time

from applications.enums import ApplicationStatus
from applications.new_schema import BerthApplicationNode, WinterStorageApplicationNode
from berth_reservations.tests.utils import (
    assert_doesnt_exist,
    assert_field_missing,
    assert_in_errors,
    assert_not_enough_permissions,
)
from contracts.models import BerthContract, WinterStorageContract
from customers.schema import BoatNode, ProfileNode
from payments.models import Order
from payments.schema import PlaceProductTaxEnum
from payments.tests.factories import BerthProductFactory, WinterStorageProductFactory
from resources.schema import BerthNode, WinterStoragePlaceNode, WinterStorageSectionNode
from utils.numbers import rounded
from utils.relay import to_global_id

from ..enums import LeaseStatus
from ..models import BerthLease, WinterStorageLease
from ..schema import BerthLeaseNode, WinterStorageLeaseNode
from ..utils import (
    calculate_winter_storage_lease_end_date,
    calculate_winter_storage_lease_start_date,
)
from .factories import BerthLeaseFactory, WinterStorageLeaseFactory

CREATE_BERTH_LEASE_MUTATION = """
mutation CreateBerthLease($input: CreateBerthLeaseMutationInput!) {
    createBerthLease(input:$input){
        berthLease {
            id
            startDate
            endDate
            customer {
              id
            }
            boat {
              id
            }
            status
            comment
            berth {
                id
            }
            application {
                id
                status
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services", "berth_handler"], indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_create_berth_lease(api_client, berth_application, berth, customer_profile):
    berth_application.customer = customer_profile
    berth_application.save()
    min_width = berth.berth_type.width - 1
    max_width = berth.berth_type.width + 1
    BerthProductFactory(min_width=min_width, max_width=max_width)

    variables = {
        "applicationId": to_global_id(BerthApplicationNode, berth_application.id),
        "berthId": to_global_id(BerthNode, berth.id),
    }

    assert BerthLease.objects.count() == 0

    executed = api_client.execute(CREATE_BERTH_LEASE_MUTATION, input=variables)

    assert BerthLease.objects.count() == 1

    assert executed["data"]["createBerthLease"]["berthLease"].pop("id") is not None
    assert executed["data"]["createBerthLease"]["berthLease"] == {
        "status": "DRAFTED",
        "startDate": "2020-06-10",
        "endDate": "2020-09-14",
        "comment": "",
        "boat": None,
        "customer": {"id": to_global_id(ProfileNode, berth_application.customer.id)},
        "application": {
            "id": variables.get("applicationId"),
            "status": ApplicationStatus.OFFER_GENERATED.name,
        },
        "berth": {"id": variables.get("berthId")},
    }


@pytest.mark.parametrize(
    "api_client", ["berth_services", "berth_handler"], indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_create_berth_lease_all_arguments(
    api_client, berth_application, berth, boat, customer_profile
):
    berth_application.customer = customer_profile
    berth_application.save()
    boat.owner = customer_profile
    boat.save()
    min_width = berth.berth_type.width - 1
    max_width = berth.berth_type.width + 1
    BerthProductFactory(min_width=min_width, max_width=max_width)

    variables = {
        "applicationId": to_global_id(BerthApplicationNode, berth_application.id),
        "berthId": to_global_id(BerthNode, berth.id),
        "boatId": to_global_id(BoatNode, boat.id),
        "startDate": "2020-03-01",
        "endDate": "2020-12-31",
        "comment": "Very wow, such comment",
    }

    assert BerthLease.objects.count() == 0

    executed = api_client.execute(CREATE_BERTH_LEASE_MUTATION, input=variables)

    assert BerthLease.objects.count() == 1

    assert executed["data"]["createBerthLease"]["berthLease"].pop("id") is not None
    assert executed["data"]["createBerthLease"]["berthLease"] == {
        "status": "DRAFTED",
        "startDate": variables.get("startDate"),
        "endDate": variables.get("endDate"),
        "comment": variables.get("comment"),
        "boat": {"id": variables.get("boatId")},
        "customer": {"id": to_global_id(ProfileNode, berth_application.customer.id)},
        "application": {
            "id": variables.get("applicationId"),
            "status": ApplicationStatus.OFFER_GENERATED.name,
        },
        "berth": {"id": variables.get("berthId")},
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services", "berth_supervisor"],
    indirect=True,
)
def test_create_berth_lease_not_enough_permissions(
    api_client, berth_application, berth
):
    variables = {
        "applicationId": to_global_id(BerthApplicationNode, berth_application.id),
        "berthId": to_global_id(BerthNode, berth.id),
    }

    executed = api_client.execute(CREATE_BERTH_LEASE_MUTATION, input=variables)

    assert_not_enough_permissions(executed)


def test_create_berth_lease_application_doesnt_exist(superuser_api_client, berth):
    variables = {
        "applicationId": to_global_id(BerthApplicationNode, randint(0, 999)),
        "berthId": to_global_id(BerthNode, berth.id),
    }

    executed = superuser_api_client.execute(
        CREATE_BERTH_LEASE_MUTATION, input=variables,
    )

    assert_doesnt_exist("BerthApplication", executed)


def test_create_berth_lease_berth_doesnt_exist(
    superuser_api_client, berth_application, customer_profile
):
    berth_application.customer = customer_profile
    berth_application.save()
    variables = {
        "applicationId": to_global_id(BerthApplicationNode, berth_application.id),
        "berthId": to_global_id(BerthNode, uuid.uuid4()),
    }

    executed = superuser_api_client.execute(
        CREATE_BERTH_LEASE_MUTATION, input=variables,
    )

    assert_doesnt_exist("Berth", executed)


def test_create_berth_lease_application_id_missing(superuser_api_client):
    variables = {
        "berthId": to_global_id(BerthNode, uuid.uuid4()),
    }

    executed = superuser_api_client.execute(
        CREATE_BERTH_LEASE_MUTATION, input=variables,
    )

    assert_field_missing("applicationId", executed)


def test_create_berth_lease_berth_id_missing(superuser_api_client):
    variables = {
        "berthId": to_global_id(BerthApplicationNode, randint(0, 999)),
    }

    executed = superuser_api_client.execute(
        CREATE_BERTH_LEASE_MUTATION, input=variables,
    )

    assert_field_missing("berthId", executed)


def test_create_berth_lease_application_without_customer(
    superuser_api_client, berth_application, berth
):
    berth_application.customer = None
    berth_application.save()

    variables = {
        "applicationId": to_global_id(BerthApplicationNode, berth_application.id),
        "berthId": to_global_id(BerthNode, berth.id),
    }

    executed = superuser_api_client.execute(
        CREATE_BERTH_LEASE_MUTATION, input=variables,
    )

    assert_in_errors(
        "Application must be connected to an existing customer first", executed
    )


def test_create_berth_lease_application_already_has_lease(
    superuser_api_client, berth_application, berth, customer_profile,
):
    BerthLeaseFactory(application=berth_application)
    berth_application.customer = customer_profile
    berth_application.save()

    variables = {
        "applicationId": to_global_id(BerthApplicationNode, berth_application.id),
        "berthId": to_global_id(BerthNode, berth.id),
    }

    executed = superuser_api_client.execute(
        CREATE_BERTH_LEASE_MUTATION, input=variables,
    )

    assert_in_errors("Berth lease with this Application already exists", executed)


CREATE_BERTH_LEASE_WITH_ORDER_MUTATION = """
mutation CreateBerthLease($input: CreateBerthLeaseMutationInput!) {
    createBerthLease(input:$input){
        berthLease {
            id
            berth {
                id
            }
            order {
                id
                price
                status
                customer {
                    id
                }
                product {
                    ... on BerthProductNode {
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
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services", "berth_handler"], indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_create_berth_lease_with_order(
    api_client, berth_application, berth, customer_profile
):
    berth_application.customer = customer_profile
    berth_application.save()
    min_width = berth.berth_type.width - 1
    max_width = berth.berth_type.width + 1
    berth_product = BerthProductFactory(min_width=min_width, max_width=max_width)

    variables = {
        "applicationId": to_global_id(BerthApplicationNode, berth_application.id),
        "berthId": to_global_id(BerthNode, berth.id),
    }

    assert BerthLease.objects.count() == 0
    assert Order.objects.count() == 0

    executed = api_client.execute(
        CREATE_BERTH_LEASE_WITH_ORDER_MUTATION, input=variables
    )

    assert BerthLease.objects.count() == 1
    assert Order.objects.count() == 1

    assert executed["data"]["createBerthLease"]["berthLease"].pop("id") is not None
    assert (
        executed["data"]["createBerthLease"]["berthLease"]["order"].pop("id")
        is not None
    )
    assert executed["data"]["createBerthLease"]["berthLease"] == {
        "berth": {"id": variables["berthId"]},
        "order": {
            "price": str(berth_product.price_for_tier(tier=berth.pier.price_tier)),
            "status": "WAITING",
            "customer": {"id": to_global_id(ProfileNode, customer_profile.id)},
            "product": {
                "minWidth": rounded(
                    berth_product.min_width, decimals=2, as_string=True
                ),
                "maxWidth": rounded(
                    berth_product.max_width, decimals=2, as_string=True
                ),
                "tier1Price": rounded(
                    berth_product.tier_1_price, decimals=2, as_string=True
                ),
                "tier2Price": rounded(
                    berth_product.tier_2_price, decimals=2, as_string=True
                ),
                "tier3Price": rounded(
                    berth_product.tier_3_price, decimals=2, as_string=True
                ),
                "priceUnit": berth_product.price_unit.name,
                "taxPercentage": PlaceProductTaxEnum.get(
                    berth_product.tax_percentage
                ).name,
            },
        },
    }


DELETE_BERTH_LEASE_MUTATION = """
mutation DELETE_DRAFTED_LEASE($input: DeleteBerthLeaseMutationInput!) {
    deleteBerthLease(input: $input) {
        __typename
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services", "berth_handler"], indirect=True,
)
def test_delete_berth_lease_drafted(berth_lease, berth_application, api_client):
    variables = {"id": to_global_id(BerthLeaseNode, berth_lease.id)}
    berth_lease.application = berth_application
    berth_lease.save()

    assert BerthLease.objects.count() == 1

    api_client.execute(
        DELETE_BERTH_LEASE_MUTATION, input=variables,
    )

    assert BerthLease.objects.count() == 0
    assert berth_application.status == ApplicationStatus.PENDING


def test_delete_berth_lease_not_drafted(berth_lease, superuser_api_client):
    berth_lease.status = LeaseStatus.OFFERED
    berth_lease.save()

    variables = {"id": to_global_id(BerthLeaseNode, berth_lease.id)}

    assert BerthLease.objects.count() == 1

    executed = superuser_api_client.execute(
        DELETE_BERTH_LEASE_MUTATION, input=variables,
    )

    assert BerthLease.objects.count() == 1
    assert_in_errors(
        f"Lease object is not DRAFTED anymore: {LeaseStatus.OFFERED}", executed
    )


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services", "berth_supervisor"],
    indirect=True,
)
def test_delete_berth_lease_not_enough_permissions(api_client, berth_lease):
    variables = {
        "id": to_global_id(BerthLeaseNode, berth_lease.id),
    }

    assert BerthLease.objects.count() == 1

    executed = api_client.execute(DELETE_BERTH_LEASE_MUTATION, input=variables)

    assert BerthLease.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_delete_berth_lease_inexistent_lease(superuser_api_client):
    variables = {
        "id": to_global_id(BerthLeaseNode, uuid.uuid4()),
    }

    executed = superuser_api_client.execute(
        DELETE_BERTH_LEASE_MUTATION, input=variables,
    )

    assert_doesnt_exist("BerthLease", executed)


UPDATE_BERTH_LEASE_MUTATION = """
mutation UpdateBerthLease($input: UpdateBerthLeaseMutationInput!) {
    updateBerthLease(input:$input){
        berthLease {
            id
            startDate
            endDate
            comment
            boat {
                id
            }
            application {
                id
                customer {
                    id
                }
            }
        }
    }
}
"""


@freeze_time("2020-01-01T08:00:00Z")
@pytest.mark.parametrize(
    "api_client", ["berth_services", "berth_handler"], indirect=True,
)
def test_update_berth_lease_all_fields(
    api_client, berth_lease, berth_application, boat, customer_profile
):
    berth_lease_id = to_global_id(BerthLeaseNode, berth_lease.id)
    application_id = to_global_id(BerthApplicationNode, berth_application.id)
    boat_id = to_global_id(BoatNode, boat.id)

    berth_application.customer = customer_profile
    berth_application.save()
    boat.owner = customer_profile
    boat.save()

    start_date = today()
    end_date = start_date + relativedelta(months=3)

    variables = {
        "id": berth_lease_id,
        "startDate": start_date,
        "endDate": end_date,
        "comment": "",
        "boatId": boat_id,
        "applicationId": application_id,
    }

    executed = api_client.execute(UPDATE_BERTH_LEASE_MUTATION, input=variables)
    assert executed["data"]["updateBerthLease"]["berthLease"] == {
        "id": berth_lease_id,
        "startDate": str(variables["startDate"].date()),
        "endDate": str(variables["endDate"].date()),
        "comment": variables["comment"],
        "boat": {"id": boat_id},
        "application": {
            "id": application_id,
            "customer": {
                "id": to_global_id(ProfileNode, berth_application.customer.id),
            },
        },
    }


@freeze_time("2020-01-01T08:00:00Z")
@pytest.mark.parametrize(
    "api_client", ["berth_services", "berth_handler"], indirect=True,
)
def test_update_berth_lease_remove_application(
    api_client, berth_lease, berth_application
):
    berth_lease_id = to_global_id(BerthLeaseNode, berth_lease.id)
    boat_id = to_global_id(BoatNode, berth_lease.boat.id)
    berth_lease.application = berth_application
    berth_lease.save()

    variables = {
        "id": berth_lease_id,
        "applicationId": None,
    }

    executed = api_client.execute(UPDATE_BERTH_LEASE_MUTATION, input=variables)
    assert executed["data"]["updateBerthLease"]["berthLease"] == {
        "id": berth_lease_id,
        "startDate": str(berth_lease.start_date),
        "endDate": str(berth_lease.end_date),
        "comment": berth_lease.comment,
        "boat": {"id": boat_id},
        "application": None,
    }


def test_update_berth_lease_application_doesnt_exist(superuser_api_client, berth_lease):
    variables = {
        "id": to_global_id(BerthLeaseNode, berth_lease.id),
        "applicationId": to_global_id(BerthApplicationNode, randint(0, 999)),
    }

    executed = superuser_api_client.execute(
        UPDATE_BERTH_LEASE_MUTATION, input=variables,
    )

    assert_doesnt_exist("BerthApplication", executed)


def test_update_berth_lease_application_without_customer(
    superuser_api_client, berth_lease, berth_application
):
    berth_application.customer = None
    berth_application.save()

    variables = {
        "id": to_global_id(BerthLeaseNode, berth_lease.id),
        "applicationId": to_global_id(BerthApplicationNode, berth_application.id),
    }

    executed = superuser_api_client.execute(
        UPDATE_BERTH_LEASE_MUTATION, input=variables,
    )

    assert_in_errors(
        "Application must be connected to an existing customer first", executed
    )


def test_update_berth_lease_application_already_has_lease(
    superuser_api_client, berth_application, berth_lease, customer_profile,
):
    BerthLeaseFactory(application=berth_application)
    berth_application.customer = customer_profile
    berth_application.save()

    variables = {
        "id": to_global_id(BerthLeaseNode, berth_lease.id),
        "applicationId": to_global_id(BerthApplicationNode, berth_application.id),
    }

    executed = superuser_api_client.execute(
        UPDATE_BERTH_LEASE_MUTATION, input=variables,
    )

    assert_in_errors("Berth lease with this Application already exists", executed)


CREATE_WINTER_STORAGE_LEASE_MUTATION = """
mutation CreateWinterStorageLease($input: CreateWinterStorageLeaseMutationInput!) {
    createWinterStorageLease(input:$input){
        winterStorageLease {
            id
            startDate
            endDate
            customer {
              id
            }
            boat {
              id
            }
            status
            comment
            place {
                id
            }
            section {
                id
            }
            application {
                id
                status
            }
            order {
                id
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services", "berth_handler"], indirect=True,
)
def test_create_winter_storage_lease(
    api_client, winter_storage_application, winter_storage_place, customer_profile
):
    WinterStorageProductFactory(
        winter_storage_area=winter_storage_place.winter_storage_section.area
    )
    winter_storage_application.customer = customer_profile
    winter_storage_application.save()

    variables = {
        "applicationId": to_global_id(
            WinterStorageApplicationNode, winter_storage_application.id
        ),
        "placeId": to_global_id(WinterStoragePlaceNode, winter_storage_place.id),
    }

    assert WinterStorageLease.objects.count() == 0

    executed = api_client.execute(CREATE_WINTER_STORAGE_LEASE_MUTATION, input=variables)

    assert WinterStorageLease.objects.count() == 1

    assert (
        executed["data"]["createWinterStorageLease"]["winterStorageLease"].pop("id")
        is not None
    )
    assert (
        executed["data"]["createWinterStorageLease"]["winterStorageLease"].pop("order")
        is not None
    )
    assert executed["data"]["createWinterStorageLease"]["winterStorageLease"] == {
        "status": "DRAFTED",
        "startDate": str(calculate_winter_storage_lease_start_date()),
        "endDate": str(calculate_winter_storage_lease_end_date()),
        "comment": "",
        "boat": None,
        "customer": {
            "id": to_global_id(ProfileNode, winter_storage_application.customer.id)
        },
        "application": {
            "id": variables.get("applicationId"),
            "status": ApplicationStatus.OFFER_GENERATED.name,
        },
        "place": {"id": variables.get("placeId")},
        "section": None,
    }


@pytest.mark.parametrize(
    "api_client", ["berth_services", "berth_handler"], indirect=True,
)
def test_create_winter_storage_lease_with_section(
    api_client, winter_storage_application, winter_storage_section, boat
):
    WinterStorageProductFactory(winter_storage_area=winter_storage_section.area)
    winter_storage_application.customer = boat.owner
    winter_storage_application.save()

    variables = {
        "applicationId": to_global_id(
            WinterStorageApplicationNode, winter_storage_application.id
        ),
        "sectionId": to_global_id(WinterStorageSectionNode, winter_storage_section.id),
        "boatId": to_global_id(BoatNode, boat.id),
    }

    assert WinterStorageLease.objects.count() == 0

    executed = api_client.execute(CREATE_WINTER_STORAGE_LEASE_MUTATION, input=variables)

    assert WinterStorageLease.objects.count() == 1

    assert (
        executed["data"]["createWinterStorageLease"]["winterStorageLease"].pop("id")
        is not None
    )
    assert (
        executed["data"]["createWinterStorageLease"]["winterStorageLease"].pop("order")
        is not None
    )
    assert executed["data"]["createWinterStorageLease"]["winterStorageLease"] == {
        "status": "DRAFTED",
        "startDate": str(calculate_winter_storage_lease_start_date()),
        "endDate": str(calculate_winter_storage_lease_end_date()),
        "comment": "",
        "boat": {"id": variables["boatId"]},
        "customer": {
            "id": to_global_id(ProfileNode, winter_storage_application.customer.id)
        },
        "application": {
            "id": variables.get("applicationId"),
            "status": ApplicationStatus.OFFER_GENERATED.name,
        },
        "place": None,
        "section": {"id": variables.get("sectionId")},
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services", "berth_supervisor"],
    indirect=True,
)
def test_create_winter_storage_lease_not_enough_permissions(
    api_client, winter_storage_application, winter_storage_place
):
    variables = {
        "applicationId": to_global_id(
            WinterStorageApplicationNode, winter_storage_application.id
        ),
        "placeId": to_global_id(WinterStoragePlaceNode, winter_storage_place.id),
    }

    executed = api_client.execute(CREATE_WINTER_STORAGE_LEASE_MUTATION, input=variables)

    assert_not_enough_permissions(executed)


def test_create_winter_storage_lease_application_doesnt_exist(
    superuser_api_client, winter_storage_place
):
    variables = {
        "applicationId": to_global_id(WinterStorageApplicationNode, randint(0, 999)),
        "placeId": to_global_id(BerthNode, winter_storage_place.id),
    }

    executed = superuser_api_client.execute(
        CREATE_WINTER_STORAGE_LEASE_MUTATION, input=variables,
    )

    assert_doesnt_exist("WinterStorageApplication", executed)


def test_create_winter_storage_lease_winter_storage_place_doesnt_exist(
    superuser_api_client, winter_storage_application, customer_profile
):
    winter_storage_application.customer = customer_profile
    winter_storage_application.save()
    variables = {
        "applicationId": to_global_id(
            WinterStorageApplicationNode, winter_storage_application.id
        ),
        "placeId": to_global_id(WinterStoragePlaceNode, uuid.uuid4()),
    }

    executed = superuser_api_client.execute(
        CREATE_WINTER_STORAGE_LEASE_MUTATION, input=variables,
    )

    assert_doesnt_exist("WinterStoragePlace", executed)


def test_create_winter_storage_lease_application_id_missing(superuser_api_client):
    variables = {
        "placeId": to_global_id(WinterStoragePlaceNode, uuid.uuid4()),
    }

    executed = superuser_api_client.execute(
        CREATE_WINTER_STORAGE_LEASE_MUTATION, input=variables,
    )

    assert_field_missing("applicationId", executed)


def test_create_winter_storage_lease_application_without_customer(
    superuser_api_client, winter_storage_application, winter_storage_place
):
    winter_storage_application.customer = None
    winter_storage_application.save()

    variables = {
        "applicationId": to_global_id(
            WinterStorageApplicationNode, winter_storage_application.id
        ),
        "placeId": to_global_id(BerthNode, winter_storage_place.id),
    }

    executed = superuser_api_client.execute(
        CREATE_WINTER_STORAGE_LEASE_MUTATION, input=variables,
    )

    assert_in_errors(
        "Application must be connected to an existing customer first", executed
    )


def test_create_winter_storage_lease_application_already_has_lease(
    superuser_api_client,
    winter_storage_application,
    winter_storage_place,
    customer_profile,
):
    WinterStorageLeaseFactory(application=winter_storage_application)
    winter_storage_application.customer = customer_profile
    winter_storage_application.save()

    variables = {
        "applicationId": to_global_id(
            WinterStorageApplicationNode, winter_storage_application.id
        ),
        "placeId": to_global_id(WinterStoragePlaceNode, winter_storage_place.id),
    }

    executed = superuser_api_client.execute(
        CREATE_WINTER_STORAGE_LEASE_MUTATION, input=variables,
    )

    assert_in_errors(
        "Winter storage lease with this Application already exists", executed
    )


def test_create_winter_storage_lease_both_place_and_section(
    superuser_api_client,
    winter_storage_application,
    winter_storage_place,
    winter_storage_section,
    customer_profile,
):
    winter_storage_application.customer = customer_profile
    winter_storage_application.save()

    variables = {
        "applicationId": to_global_id(
            WinterStorageApplicationNode, winter_storage_application.id
        ),
        "placeId": to_global_id(WinterStoragePlaceNode, winter_storage_place.id),
        "sectionId": to_global_id(WinterStorageSectionNode, winter_storage_section.id),
    }

    executed = superuser_api_client.execute(
        CREATE_WINTER_STORAGE_LEASE_MUTATION, input=variables,
    )

    assert_in_errors("Cannot receive both Winter Storage Place and Section", executed)


def test_create_winter_storage_lease_no_place_or_section(
    superuser_api_client, winter_storage_application, customer_profile,
):
    winter_storage_application.customer = customer_profile
    winter_storage_application.save()

    variables = {
        "applicationId": to_global_id(
            WinterStorageApplicationNode, winter_storage_application.id
        ),
    }

    executed = superuser_api_client.execute(
        CREATE_WINTER_STORAGE_LEASE_MUTATION, input=variables,
    )

    assert_in_errors("Either Winter Storage Place or Section are required", executed)


CREATE_WINTER_STORAGE_LEASE_WITH_ORDER_MUTATION = """
mutation CreateWinterStorageLease($input: CreateWinterStorageLeaseMutationInput!) {
    createWinterStorageLease(input:$input){
        winterStorageLease {
            id
            place {
                id
            }
            order {
                id
                price
                status
                customer {
                    id
                }
                product {
                    ... on WinterStorageProductNode {
                        priceUnit
                        priceValue
                    }
                }
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services", "berth_handler"], indirect=True,
)
@freeze_time("2020-06-11T08:00:00Z")
def test_create_winter_storage_lease_with_order(
    api_client, winter_storage_application, winter_storage_place, customer_profile
):
    winter_storage_application.customer = customer_profile
    winter_storage_application.save()
    product = WinterStorageProductFactory(
        winter_storage_area=winter_storage_place.winter_storage_section.area
    )

    variables = {
        "applicationId": to_global_id(
            WinterStorageApplicationNode, winter_storage_application.id
        ),
        "placeId": to_global_id(WinterStoragePlaceNode, winter_storage_place.id),
    }

    assert WinterStorageLease.objects.count() == 0
    assert Order.objects.count() == 0

    executed = api_client.execute(
        CREATE_WINTER_STORAGE_LEASE_WITH_ORDER_MUTATION, input=variables
    )

    assert WinterStorageLease.objects.count() == 1
    assert Order.objects.count() == 1
    sqm = winter_storage_place.place_type.width * winter_storage_place.place_type.length
    expected_price = product.price_value
    expected_price = rounded(expected_price * sqm, decimals=2, as_string=True)

    assert (
        executed["data"]["createWinterStorageLease"]["winterStorageLease"].pop("id")
        is not None
    )
    assert (
        executed["data"]["createWinterStorageLease"]["winterStorageLease"]["order"].pop(
            "id"
        )
        is not None
    )
    assert executed["data"]["createWinterStorageLease"]["winterStorageLease"] == {
        "place": {"id": variables["placeId"]},
        "order": {
            "price": expected_price,
            "status": "WAITING",
            "customer": {"id": to_global_id(ProfileNode, customer_profile.id)},
            "product": {
                "priceUnit": product.price_unit.name,
                "priceValue": str(product.price_value),
            },
        },
    }


@pytest.mark.parametrize(
    "api_client", ["berth_services", "berth_handler"], indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_create_winter_storage_lease_with_order_no_product(
    api_client, winter_storage_application, winter_storage_place, customer_profile
):
    winter_storage_application.customer = customer_profile
    winter_storage_application.save()

    variables = {
        "applicationId": to_global_id(
            WinterStorageApplicationNode, winter_storage_application.id
        ),
        "placeId": to_global_id(WinterStoragePlaceNode, winter_storage_place.id),
    }

    assert WinterStorageLease.objects.count() == 0
    assert Order.objects.count() == 0

    executed = api_client.execute(
        CREATE_WINTER_STORAGE_LEASE_WITH_ORDER_MUTATION, input=variables
    )

    assert WinterStorageLease.objects.count() == 0
    assert Order.objects.count() == 0
    assert_doesnt_exist("WinterStorageProduct", executed)


DELETE_WINTER_STORAGE_LEASE_MUTATION = """
mutation DELETE_DRAFTED_LEASE($input: DeleteWinterStorageLeaseMutationInput!) {
    deleteWinterStorageLease(input: $input) {
        __typename
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services", "berth_handler"], indirect=True,
)
def test_delete_winter_storage_lease_drafted(
    winter_storage_lease, winter_storage_application, api_client
):
    variables = {"id": to_global_id(WinterStorageLeaseNode, winter_storage_lease.id)}
    winter_storage_lease.application = winter_storage_application
    winter_storage_lease.save()

    assert WinterStorageLease.objects.count() == 1

    api_client.execute(
        DELETE_WINTER_STORAGE_LEASE_MUTATION, input=variables,
    )

    assert WinterStorageLease.objects.count() == 0
    assert winter_storage_application.status == ApplicationStatus.PENDING


def test_delete_winter_storage_lease_not_drafted(
    winter_storage_lease, superuser_api_client
):
    winter_storage_lease.status = LeaseStatus.OFFERED
    winter_storage_lease.save()

    variables = {"id": to_global_id(WinterStorageLeaseNode, winter_storage_lease.id)}

    assert WinterStorageLease.objects.count() == 1

    executed = superuser_api_client.execute(
        DELETE_WINTER_STORAGE_LEASE_MUTATION, input=variables,
    )

    assert WinterStorageLease.objects.count() == 1
    assert_in_errors(
        f"Lease object is not DRAFTED anymore: {LeaseStatus.OFFERED}", executed
    )


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services", "berth_supervisor"],
    indirect=True,
)
def test_delete_winter_storage_lease_not_enough_permissions(
    api_client, winter_storage_lease
):
    variables = {
        "id": to_global_id(BerthLeaseNode, winter_storage_lease.id),
    }

    assert WinterStorageLease.objects.count() == 1

    executed = api_client.execute(DELETE_WINTER_STORAGE_LEASE_MUTATION, input=variables)

    assert WinterStorageLease.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_delete_winter_storage_lease_inexistent_lease(superuser_api_client):
    variables = {
        "id": to_global_id(WinterStorageLeaseNode, uuid.uuid4()),
    }

    executed = superuser_api_client.execute(
        DELETE_WINTER_STORAGE_LEASE_MUTATION, input=variables,
    )

    assert_doesnt_exist("WinterStorageLease", executed)


UPDATE_WINTER_STORAGE_LEASE_MUTATION = """
mutation UpdateWinterStorageLease($input: UpdateWinterStorageLeaseMutationInput!) {
    updateWinterStorageLease(input:$input){
        winterStorageLease {
            id
            startDate
            endDate
            comment
            boat {
                id
            }
            application {
                id
                customer {
                    id
                }
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services", "berth_handler"], indirect=True,
)
def test_update_winter_storage_lease_all_fields(
    api_client, winter_storage_lease, winter_storage_application, boat, customer_profile
):
    lease_id = to_global_id(WinterStorageLeaseNode, winter_storage_lease.id)
    application_id = to_global_id(
        WinterStorageApplicationNode, winter_storage_application.id
    )
    boat_id = to_global_id(BoatNode, boat.id)

    winter_storage_application.customer = customer_profile
    winter_storage_application.save()
    boat.owner = customer_profile
    boat.save()

    start_date = today()
    end_date = start_date + relativedelta(months=3)

    variables = {
        "id": lease_id,
        "startDate": start_date,
        "endDate": end_date,
        "comment": "",
        "boatId": boat_id,
        "applicationId": application_id,
    }

    executed = api_client.execute(UPDATE_WINTER_STORAGE_LEASE_MUTATION, input=variables)
    assert executed["data"]["updateWinterStorageLease"]["winterStorageLease"] == {
        "id": lease_id,
        "startDate": str(variables["startDate"].date()),
        "endDate": str(variables["endDate"].date()),
        "comment": variables["comment"],
        "boat": {"id": boat_id},
        "application": {
            "id": application_id,
            "customer": {
                "id": to_global_id(ProfileNode, winter_storage_application.customer.id),
            },
        },
    }


@pytest.mark.parametrize(
    "api_client", ["berth_services", "berth_handler"], indirect=True,
)
def test_update_winter_storage_lease_remove_application(
    api_client, winter_storage_lease, winter_storage_application
):
    lease_id = to_global_id(WinterStorageLeaseNode, winter_storage_lease.id)
    boat_id = to_global_id(BoatNode, winter_storage_lease.boat.id)
    winter_storage_lease.application = winter_storage_application
    winter_storage_lease.save()

    variables = {
        "id": lease_id,
        "applicationId": None,
    }

    executed = api_client.execute(UPDATE_WINTER_STORAGE_LEASE_MUTATION, input=variables)
    assert executed["data"]["updateWinterStorageLease"]["winterStorageLease"] == {
        "id": lease_id,
        "startDate": str(winter_storage_lease.start_date),
        "endDate": str(winter_storage_lease.end_date),
        "comment": winter_storage_lease.comment,
        "boat": {"id": boat_id},
        "application": None,
    }


def test_update_winter_storage_lease_application_doesnt_exist(
    superuser_api_client, winter_storage_lease
):
    variables = {
        "id": to_global_id(WinterStorageLeaseNode, winter_storage_lease.id),
        "applicationId": to_global_id(WinterStorageApplicationNode, randint(0, 999)),
    }

    executed = superuser_api_client.execute(
        UPDATE_WINTER_STORAGE_LEASE_MUTATION, input=variables,
    )

    assert_doesnt_exist("WinterStorageApplication", executed)


def test_update_winter_storage_lease_application_without_customer(
    superuser_api_client, winter_storage_lease, winter_storage_application
):
    winter_storage_application.customer = None
    winter_storage_application.save()

    variables = {
        "id": to_global_id(WinterStorageLeaseNode, winter_storage_lease.id),
        "applicationId": to_global_id(
            WinterStorageApplicationNode, winter_storage_application.id
        ),
    }

    executed = superuser_api_client.execute(
        UPDATE_WINTER_STORAGE_LEASE_MUTATION, input=variables,
    )

    assert_in_errors(
        "Application must be connected to an existing customer first", executed
    )


def test_update_winter_storage_lease_application_already_has_lease(
    superuser_api_client,
    winter_storage_application,
    winter_storage_lease,
    customer_profile,
):
    WinterStorageLeaseFactory(application=winter_storage_application)
    winter_storage_application.customer = customer_profile
    winter_storage_application.save()

    variables = {
        "id": to_global_id(WinterStorageLeaseNode, winter_storage_lease.id),
        "applicationId": to_global_id(
            WinterStorageApplicationNode, winter_storage_application.id
        ),
    }

    executed = superuser_api_client.execute(
        UPDATE_WINTER_STORAGE_LEASE_MUTATION, input=variables,
    )

    assert_in_errors(
        "Winter storage lease with this Application already exists", executed
    )


@pytest.mark.parametrize(
    "api_client", ["berth_services", "berth_handler"], indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_create_berth_lease_for_non_billable_customer(
    api_client, berth_application, berth, non_billable_customer
):
    berth_application.customer = non_billable_customer
    berth_application.save()
    min_width = berth.berth_type.width - 1
    max_width = berth.berth_type.width + 1
    berth_product = BerthProductFactory(min_width=min_width, max_width=max_width)

    variables = {
        "applicationId": to_global_id(BerthApplicationNode, berth_application.id),
        "berthId": to_global_id(BerthNode, berth.id),
    }

    executed = api_client.execute(
        CREATE_BERTH_LEASE_WITH_ORDER_MUTATION, input=variables
    )

    assert executed["data"]["createBerthLease"]["berthLease"].pop("id") is not None
    assert (
        executed["data"]["createBerthLease"]["berthLease"]["order"].pop("id")
        is not None
    )
    assert executed["data"]["createBerthLease"]["berthLease"] == {
        "berth": {"id": variables["berthId"]},
        "order": {
            "price": "0.00",
            "status": "PAID",
            "customer": {"id": to_global_id(ProfileNode, non_billable_customer.id)},
            "product": {
                "minWidth": rounded(
                    berth_product.min_width, decimals=2, as_string=True
                ),
                "maxWidth": rounded(
                    berth_product.max_width, decimals=2, as_string=True
                ),
                "tier1Price": rounded(
                    berth_product.tier_1_price, decimals=2, as_string=True
                ),
                "tier2Price": rounded(
                    berth_product.tier_2_price, decimals=2, as_string=True
                ),
                "tier3Price": rounded(
                    berth_product.tier_3_price, decimals=2, as_string=True
                ),
                "priceUnit": berth_product.price_unit.name,
                "taxPercentage": PlaceProductTaxEnum.get(
                    berth_product.tax_percentage
                ).name,
            },
        },
    }


@pytest.mark.parametrize(
    "api_client", ["berth_services", "berth_handler"], indirect=True,
)
@freeze_time("2020-06-11T08:00:00Z")
def test_create_winter_storage_lease_for_non_billable_customer(
    api_client,
    winter_storage_application,
    winter_storage_place,
    customer_profile,
    non_billable_customer,
):
    winter_storage_application.customer = non_billable_customer
    winter_storage_application.save()
    product = WinterStorageProductFactory(
        winter_storage_area=winter_storage_place.winter_storage_section.area
    )

    variables = {
        "applicationId": to_global_id(
            WinterStorageApplicationNode, winter_storage_application.id
        ),
        "placeId": to_global_id(WinterStoragePlaceNode, winter_storage_place.id),
    }

    executed = api_client.execute(
        CREATE_WINTER_STORAGE_LEASE_WITH_ORDER_MUTATION, input=variables
    )

    assert (
        executed["data"]["createWinterStorageLease"]["winterStorageLease"].pop("id")
        is not None
    )
    assert (
        executed["data"]["createWinterStorageLease"]["winterStorageLease"]["order"].pop(
            "id"
        )
        is not None
    )
    assert executed["data"]["createWinterStorageLease"]["winterStorageLease"] == {
        "place": {"id": variables["placeId"]},
        "order": {
            "price": "0.00",
            "status": "PAID",
            "customer": {"id": to_global_id(ProfileNode, non_billable_customer.id)},
            "product": {
                "priceUnit": product.price_unit.name,
                "priceValue": str(product.price_value),
            },
        },
    }


@pytest.mark.parametrize(
    "api_client", ["berth_services", "berth_handler"], indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_create_berth_lease_creates_contract(
    api_client, berth_application, berth, boat, customer_profile
):
    berth_application.customer = customer_profile
    berth_application.save()
    boat.owner = customer_profile
    boat.save()
    min_width = berth.berth_type.width - 1
    max_width = berth.berth_type.width + 1
    BerthProductFactory(min_width=min_width, max_width=max_width)

    variables = {
        "applicationId": to_global_id(BerthApplicationNode, berth_application.id),
        "berthId": to_global_id(BerthNode, berth.id),
        "boatId": to_global_id(BoatNode, boat.id),
        "startDate": "2020-03-01",
        "endDate": "2020-12-31",
        "comment": "Very wow, such comment",
    }

    assert BerthLease.objects.count() == 0

    api_client.execute(CREATE_BERTH_LEASE_MUTATION, input=variables)

    assert BerthLease.objects.count() == 1

    lease = BerthLease.objects.all()[:1].get()
    contract = lease.contract

    assert isinstance(contract, BerthContract)


@pytest.mark.parametrize(
    "api_client", ["berth_services", "berth_handler"], indirect=True,
)
def test_create_winter_storage_lease_creates_contract(
    api_client, winter_storage_application, winter_storage_place, customer_profile
):
    WinterStorageProductFactory(
        winter_storage_area=winter_storage_place.winter_storage_section.area
    )
    winter_storage_application.customer = customer_profile
    winter_storage_application.save()

    variables = {
        "applicationId": to_global_id(
            WinterStorageApplicationNode, winter_storage_application.id
        ),
        "placeId": to_global_id(WinterStoragePlaceNode, winter_storage_place.id),
    }

    assert WinterStorageLease.objects.count() == 0

    api_client.execute(CREATE_WINTER_STORAGE_LEASE_MUTATION, input=variables)

    assert WinterStorageLease.objects.count() == 1

    lease = WinterStorageLease.objects.all()[:1].get()
    contract = lease.contract

    assert isinstance(contract, WinterStorageContract)
