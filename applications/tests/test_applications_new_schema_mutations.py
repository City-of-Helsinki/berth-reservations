import pytest
from graphql_relay import to_global_id

from berth_reservations.tests.utils import (
    assert_field_missing,
    assert_not_enough_permissions,
    GraphQLTestClient,
)

client = GraphQLTestClient()

GRAPHQL_URL = "/graphql_v2/"

UPDATE_BERTH_APPLICATION_MUTATION = """
mutation UpdateApplication($input: UpdateBerthApplicationInput!) {
    updateBerthApplication(input: $input) {
        berthApplication {
            id
            customer {
                id
                comment
            }
        }
    }
}
"""


def test_update_berth_application(superuser, berth_application, customer_profile):
    berth_application_id = to_global_id(
        "BerthApplicationNode", str(berth_application.id)
    )
    customer_id = to_global_id("BerthProfileNode", str(customer_profile.id))

    variables = {
        "id": berth_application_id,
        "customerId": customer_id,
    }

    assert berth_application.customer is None

    executed = client.execute(
        query=UPDATE_BERTH_APPLICATION_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert executed == {
        "data": {
            "updateBerthApplication": {
                "berthApplication": {
                    "id": berth_application_id,
                    "customer": {
                        "id": customer_id,
                        "comment": customer_profile.comment,
                    },
                }
            }
        }
    }


def test_update_berth_application_no_application_id(superuser, customer_profile):
    variables = {
        "customerId": to_global_id("BerthProfileNode", str(customer_profile.id)),
    }

    executed = client.execute(
        query=UPDATE_BERTH_APPLICATION_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert_field_missing("id", executed)


def test_update_berth_application_no_customer_id(superuser, berth_application):
    variables = {
        "id": to_global_id("BerthApplicationNode", str(berth_application.id)),
    }

    executed = client.execute(
        query=UPDATE_BERTH_APPLICATION_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert_field_missing("customerId", executed)


@pytest.mark.parametrize("user", ["none", "base", "staff"], indirect=True)
def test_update_berth_application_not_enough_permissions(
    user, berth_application, customer_profile
):
    berth_application_id = to_global_id(
        "BerthApplicationNode", str(berth_application.id)
    )
    customer_id = to_global_id("BerthProfileNode", str(customer_profile.id))

    variables = {
        "id": berth_application_id,
        "customerId": customer_id,
    }

    executed = client.execute(
        query=UPDATE_BERTH_APPLICATION_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=user,
    )

    assert berth_application.customer is None
    assert_not_enough_permissions(executed)
