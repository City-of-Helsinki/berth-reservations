import uuid
from random import randint

import pytest
from freezegun import freeze_time
from graphql_relay import to_global_id

from applications.enums import ApplicationStatus
from applications.new_schema import BerthApplicationNode
from berth_reservations.tests.utils import (
    assert_doesnt_exist,
    assert_field_missing,
    assert_in_errors,
    assert_not_enough_permissions,
)
from customers.schema import BerthProfileNode, BoatNode
from leases.enums import LeaseStatus
from leases.models import BerthLease
from leases.schema import BerthLeaseNode
from leases.tests.factories import BerthLeaseFactory
from resources.schema import BerthNode

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
        "applicationId": to_global_id(
            BerthApplicationNode._meta.name, berth_application.id
        ),
        "berthId": to_global_id(BerthNode._meta.name, berth.id),
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
        "customer": {
            "id": to_global_id(
                BerthProfileNode._meta.name, berth_application.customer.id
            )
        },
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
        "applicationId": to_global_id(
            BerthApplicationNode._meta.name, berth_application.id
        ),
        "berthId": to_global_id(BerthNode._meta.name, berth.id),
        "boatId": to_global_id(BoatNode._meta.name, boat.id),
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
        "customer": {
            "id": to_global_id(
                BerthProfileNode._meta.name, berth_application.customer.id
            )
        },
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
        "applicationId": to_global_id(
            BerthApplicationNode._meta.name, berth_application.id
        ),
        "berthId": to_global_id(BerthNode._meta.name, berth.id),
    }

    executed = api_client.execute(CREATE_BERTH_LEASE_MUTATION, input=variables)

    assert_not_enough_permissions(executed)


def test_create_berth_lease_application_doesnt_exist(superuser_api_client, berth):
    variables = {
        "applicationId": to_global_id(BerthApplicationNode._meta.name, randint(0, 999)),
        "berthId": to_global_id(BerthNode._meta.name, berth.id),
    }

    executed = superuser_api_client.execute(
        CREATE_BERTH_LEASE_MUTATION, input=variables,
    )

    assert_doesnt_exist("BerthApplication", executed)


def test_create_berth_lease_berth_doesnt_exist(superuser_api_client, berth_application):
    variables = {
        "applicationId": to_global_id(
            BerthApplicationNode._meta.name, berth_application.id
        ),
        "berthId": to_global_id(BerthNode._meta.name, uuid.uuid4()),
    }

    executed = superuser_api_client.execute(
        CREATE_BERTH_LEASE_MUTATION, input=variables,
    )

    assert_doesnt_exist("Berth", executed)


def test_create_berth_lease_application_id_missing(superuser_api_client):
    variables = {
        "berthId": to_global_id(BerthNode._meta.name, uuid.uuid4()),
    }

    executed = superuser_api_client.execute(
        CREATE_BERTH_LEASE_MUTATION, input=variables,
    )

    assert_field_missing("applicationId", executed)


def test_create_berth_lease_berth_id_missing(superuser_api_client):
    variables = {
        "berthId": to_global_id(BerthApplicationNode._meta.name, randint(0, 999)),
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
        "applicationId": to_global_id(
            BerthApplicationNode._meta.name, berth_application.id
        ),
        "berthId": to_global_id(BerthNode._meta.name, berth.id),
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
        "applicationId": to_global_id(
            BerthApplicationNode._meta.name, berth_application.id
        ),
        "berthId": to_global_id(BerthNode._meta.name, berth.id),
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
    variables = {"id": to_global_id(BerthLeaseNode._meta.name, berth_lease.id)}
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

    variables = {"id": to_global_id(BerthLeaseNode._meta.name, berth_lease.id)}

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
        "id": to_global_id(BerthLeaseNode._meta.name, berth_lease.id),
    }

    assert BerthLease.objects.count() == 1

    executed = api_client.execute(DELETE_BERTH_LEASE_MUTATION, input=variables)

    assert BerthLease.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_delete_berth_lease_inexistent_lease(superuser_api_client):
    variables = {
        "id": to_global_id(BerthLeaseNode._meta.name, uuid.uuid4()),
    }

    executed = superuser_api_client.execute(
        DELETE_BERTH_LEASE_MUTATION, input=variables,
    )

    assert_doesnt_exist("BerthLease", executed)
