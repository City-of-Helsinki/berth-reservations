import uuid
from random import randint

import pytest
from freezegun import freeze_time
from graphql_relay import to_global_id

from berth_reservations.tests.utils import (
    assert_doesnt_exist,
    assert_field_missing,
    assert_in_errors,
    assert_not_enough_permissions,
    GraphQLTestClient,
)
from leases.models import BerthLease

client = GraphQLTestClient()

GRAPHQL_URL = "/graphql_v2/"

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
            }
        }
    }
}
"""


@freeze_time("2020-01-01T08:00:00Z")
def test_create_berth_lease(superuser, berth_application, berth, customer_profile):
    berth_application.customer = customer_profile
    berth_application.save()

    variables = {
        "applicationId": to_global_id("BerthApplicationNode", berth_application.id),
        "berthId": to_global_id("BerthNode", berth.id),
    }

    assert BerthLease.objects.count() == 0

    executed = client.execute(
        query=CREATE_BERTH_LEASE_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert BerthLease.objects.count() == 1

    assert executed["data"]["createBerthLease"]["berthLease"].pop("id") is not None
    assert executed["data"]["createBerthLease"]["berthLease"] == {
        "status": "DRAFTED",
        "startDate": "2020-06-10",
        "endDate": "2020-09-14",
        "comment": "",
        "boat": None,
        "customer": {
            "id": to_global_id("BerthProfileNode", berth_application.customer.id)
        },
        "application": {"id": variables.get("applicationId")},
        "berth": {"id": variables.get("berthId")},
    }


@freeze_time("2020-01-01T08:00:00Z")
def test_create_berth_lease_all_arguments(
    superuser, berth_application, berth, boat, customer_profile
):
    berth_application.customer = customer_profile
    berth_application.save()
    boat.owner = customer_profile
    boat.save()

    variables = {
        "applicationId": to_global_id("BerthApplicationNode", berth_application.id),
        "berthId": to_global_id("BerthNode", berth.id),
        "boatId": str(boat.id),
        "startDate": "2020-03-01",
        "endDate": "2020-12-31",
        "comment": "Very wow, such comment",
    }

    assert BerthLease.objects.count() == 0

    executed = client.execute(
        query=CREATE_BERTH_LEASE_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert BerthLease.objects.count() == 1

    assert executed["data"]["createBerthLease"]["berthLease"].pop("id") is not None
    assert executed["data"]["createBerthLease"]["berthLease"] == {
        "status": "DRAFTED",
        "startDate": variables.get("startDate"),
        "endDate": variables.get("endDate"),
        "comment": variables.get("comment"),
        "boat": {"id": variables.get("boatId")},
        "customer": {
            "id": to_global_id("BerthProfileNode", berth_application.customer.id)
        },
        "application": {"id": variables.get("applicationId")},
        "berth": {"id": variables.get("berthId")},
    }


@pytest.mark.parametrize("user", ["none", "base", "staff"], indirect=True)
def test_create_berth_lease_not_enough_permissions(user, berth_application, berth):
    variables = {
        "applicationId": to_global_id("BerthApplicationNode", berth_application.id),
        "berthId": to_global_id("BerthNode", berth.id),
    }

    executed = client.execute(
        query=CREATE_BERTH_LEASE_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=user,
    )

    assert_not_enough_permissions(executed)


def test_create_berth_lease_application_doesnt_exist(superuser, berth):
    variables = {
        "applicationId": to_global_id("BerthApplicationNode", randint(0, 999)),
        "berthId": to_global_id("BerthNode", berth.id),
    }

    executed = client.execute(
        query=CREATE_BERTH_LEASE_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert_doesnt_exist("BerthApplication", executed)


def test_create_berth_lease_berth_doesnt_exist(superuser, berth_application):
    variables = {
        "applicationId": to_global_id("BerthApplicationNode", berth_application.id),
        "berthId": to_global_id("BerthNode", uuid.uuid4()),
    }

    executed = client.execute(
        query=CREATE_BERTH_LEASE_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert_doesnt_exist("Berth", executed)


def test_create_berth_lease_application_id_missing(superuser):
    variables = {
        "berthId": to_global_id("BerthNode", uuid.uuid4()),
    }

    executed = client.execute(
        query=CREATE_BERTH_LEASE_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert_field_missing("applicationId", executed)


def test_create_berth_lease_berth_id_missing(superuser):
    variables = {
        "berthId": to_global_id("BerthApplicationNode", randint(0, 999)),
    }

    executed = client.execute(
        query=CREATE_BERTH_LEASE_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert_field_missing("berthId", executed)


def test_create_berth_lease_application_without_customer(
    superuser, berth_application, berth
):
    berth_application.customer = None
    berth_application.save()

    variables = {
        "applicationId": to_global_id("BerthApplicationNode", berth_application.id),
        "berthId": to_global_id("BerthNode", berth.id),
    }

    executed = client.execute(
        query=CREATE_BERTH_LEASE_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert_in_errors(
        "Application must be connected to an existing customer first", executed
    )
