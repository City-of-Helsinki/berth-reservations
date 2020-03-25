import pytest
from graphql_relay import to_global_id

from applications.new_schema import BerthApplicationNode
from berth_reservations.tests.utils import (
    assert_field_missing,
    assert_not_enough_permissions,
)
from customers.schema import BerthProfileNode

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


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
def test_update_berth_application(api_client, berth_application, customer_profile):
    berth_application_id = to_global_id(
        BerthApplicationNode._meta.name, str(berth_application.id)
    )
    customer_id = to_global_id(BerthProfileNode._meta.name, str(customer_profile.id))

    variables = {
        "id": berth_application_id,
        "customerId": customer_id,
    }

    assert berth_application.customer is None

    executed = api_client.execute(UPDATE_BERTH_APPLICATION_MUTATION, input=variables)

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


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
def test_update_berth_application_no_application_id(api_client, customer_profile):
    variables = {
        "customerId": to_global_id(
            BerthProfileNode._meta.name, str(customer_profile.id)
        ),
    }

    executed = api_client.execute(UPDATE_BERTH_APPLICATION_MUTATION, input=variables)

    assert_field_missing("id", executed)


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
def test_update_berth_application_no_customer_id(api_client, berth_application):
    variables = {
        "id": to_global_id(BerthApplicationNode._meta.name, str(berth_application.id)),
    }

    executed = api_client.execute(UPDATE_BERTH_APPLICATION_MUTATION, input=variables)

    assert_field_missing("customerId", executed)


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "berth_handler", "berth_supervisor", "harbor_services", "user"],
    indirect=True,
)
def test_update_berth_application_not_enough_permissions(
    api_client, berth_application, customer_profile
):
    berth_application_id = to_global_id(
        BerthApplicationNode._meta.name, str(berth_application.id)
    )
    customer_id = to_global_id(BerthProfileNode._meta.name, str(customer_profile.id))

    variables = {
        "id": berth_application_id,
        "customerId": customer_id,
    }

    executed = api_client.execute(UPDATE_BERTH_APPLICATION_MUTATION, input=variables)

    assert berth_application.customer is None
    assert_not_enough_permissions(executed)
