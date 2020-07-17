import uuid
from random import randint

import pytest
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
from customers.schema import BoatNode, ProfileNode
from resources.schema import BerthNode, WinterStoragePlaceNode
from utils.relay import to_global_id

from ..enums import LeaseStatus
from ..models import BerthLease, WinterStorageLease
from ..schema import BerthLeaseNode, WinterStorageLeaseNode
from ..tests.factories import BerthLeaseFactory, WinterStorageLeaseFactory
from ..utils import (
    calculate_winter_storage_lease_end_date,
    calculate_winter_storage_lease_start_date,
)

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
    end_date = start_date.replace(month=start_date.month + 3)

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
def test_create_winter_storage_lease(
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

    executed = api_client.execute(CREATE_WINTER_STORAGE_LEASE_MUTATION, input=variables)

    assert WinterStorageLease.objects.count() == 1

    assert (
        executed["data"]["createWinterStorageLease"]["winterStorageLease"].pop("id")
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


def test_create_winter_storage_lease_berth_id_missing(superuser_api_client):
    variables = {
        "applicationId": to_global_id(WinterStorageApplicationNode, randint(0, 999)),
    }

    executed = superuser_api_client.execute(
        CREATE_WINTER_STORAGE_LEASE_MUTATION, input=variables,
    )

    assert_field_missing("placeId", executed)


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
    end_date = start_date.replace(month=start_date.month + 3)

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
