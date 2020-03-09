import pytest
from graphql_relay import to_global_id

from berth_reservations.tests.utils import (
    assert_field_missing,
    assert_not_enough_permissions,
)

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


def test_update_berth_application(
    superuser_api_client, berth_application, customer_profile
):
    berth_application_id = to_global_id(
        "BerthApplicationNode", str(berth_application.id)
    )
    customer_id = to_global_id("BerthProfileNode", str(customer_profile.id))

    variables = {
        "id": berth_application_id,
        "customerId": customer_id,
    }

    assert berth_application.customer is None

    executed = superuser_api_client.execute(
        UPDATE_BERTH_APPLICATION_MUTATION, input=variables,
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


def test_update_berth_application_no_application_id(
    superuser_api_client, customer_profile
):
    variables = {
        "customerId": to_global_id("BerthProfileNode", str(customer_profile.id)),
    }

    executed = superuser_api_client.execute(
        UPDATE_BERTH_APPLICATION_MUTATION, input=variables,
    )

    assert_field_missing("id", executed)


def test_update_berth_application_no_customer_id(
    superuser_api_client, berth_application
):
    variables = {
        "id": to_global_id("BerthApplicationNode", str(berth_application.id)),
    }

    executed = superuser_api_client.execute(
        UPDATE_BERTH_APPLICATION_MUTATION, input=variables,
    )

    assert_field_missing("customerId", executed)


@pytest.mark.parametrize(
    "api_client", ["api_client", "user_api_client", "staff_api_client"], indirect=True
)
def test_update_berth_application_not_enough_permissions(
    api_client, berth_application, customer_profile
):
    berth_application_id = to_global_id(
        "BerthApplicationNode", str(berth_application.id)
    )
    customer_id = to_global_id("BerthProfileNode", str(customer_profile.id))

    variables = {
        "id": berth_application_id,
        "customerId": customer_id,
    }

    executed = api_client.execute(UPDATE_BERTH_APPLICATION_MUTATION, input=variables)

    assert berth_application.customer is None
    assert_not_enough_permissions(executed)
