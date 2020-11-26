from unittest import mock

import pytest
from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from freezegun import freeze_time
from graphql_relay import from_global_id

from berth_reservations.tests.factories import UserFactory
from berth_reservations.tests.utils import assert_not_enough_permissions
from customers.schema import ProfileNode
from customers.tests.conftest import mocked_response_profile
from payments.models import BerthPriceGroup, Order
from payments.tests.factories import BerthProductFactory
from utils.relay import to_global_id

from ..enums import LeaseStatus
from ..utils import calculate_season_end_date, calculate_season_start_date
from .factories import BerthLeaseFactory

PROFILE_TOKEN_SERVICE = "http://fake-profile-api.com"

SEND_EXISTING_INVOICES_MUTATION = """
mutation SendExistingBerthInvoices($input: SendExistingBerthInvoicesMutationInput!) {
    sendExistingBerthInvoices(input: $input) {
        result{
            successful_orders: successfulOrders
            failed_orders: failedOrders {
                id
                error
            }
            failed_leases: failedLeases {
                id
                error
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_send_berth_invoices_success(api_client, notification_template_orders_approved):
    lease = BerthLeaseFactory(
        renew_automatically=True,
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_season_start_date(today() - relativedelta(years=1)),
        end_date=calculate_season_end_date(today() - relativedelta(years=1)),
    )
    customer = lease.customer
    price_group = BerthPriceGroup.objects.get_or_create_for_width(
        lease.berth.berth_type.width
    )
    BerthProductFactory(price_group=price_group, harbor=lease.berth.pier.harbor)

    user = UserFactory()

    # Add the tokens to the headers
    api_client.execute_options["context"].META[
        "HTTP_API_TOKENS"
    ] = f'{{"{PROFILE_TOKEN_SERVICE}": "token"}}'

    data = {
        "id": to_global_id(ProfileNode, customer.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "primary_email": {"email": user.email},
    }

    assert Order.objects.count() == 0

    variables = {"dueDate": "2020-01-31"}

    with mock.patch(
        "customers.services.profile.requests.post",
        side_effect=mocked_response_profile(count=0, data=data),
    ):
        executed = api_client.execute(SEND_EXISTING_INVOICES_MUTATION, input=variables,)

    result = executed["data"]["sendExistingBerthInvoices"]["result"]
    assert len(result.get("successful_orders")) == 1
    assert len(result.get("failed_orders")) == 0
    assert len(result.get("failed_leases")) == 0

    assert from_global_id(result.get("successful_orders")[0])[0] == "OrderNode"


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services", "berth_supervisor"],
    indirect=True,
)
def test_send_berth_invoices_not_enough_permissions(
    api_client, berth_application, berth
):
    variables = {"dueDate": "2020-01-31"}

    executed = api_client.execute(SEND_EXISTING_INVOICES_MUTATION, input=variables,)

    assert_not_enough_permissions(executed)


@freeze_time("2020-01-01T08:00:00Z")
def test_send_berth_invoices_missing_email(
    superuser_api_client, notification_template_orders_approved
):
    lease = BerthLeaseFactory(
        renew_automatically=True,
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_season_start_date(today() - relativedelta(years=1)),
        end_date=calculate_season_end_date(today() - relativedelta(years=1)),
    )
    customer = lease.customer
    price_group = BerthPriceGroup.objects.get_or_create_for_width(
        lease.berth.berth_type.width
    )
    BerthProductFactory(price_group=price_group, harbor=lease.berth.pier.harbor)

    user = UserFactory()

    # Add the tokens to the headers
    superuser_api_client.execute_options["context"].META[
        "HTTP_API_TOKENS"
    ] = f'{{"{PROFILE_TOKEN_SERVICE}": "token"}}'

    data = {
        "id": to_global_id(ProfileNode, customer.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "primary_email": None,
    }

    assert Order.objects.count() == 0

    variables = {"dueDate": "2020-01-31"}

    with mock.patch(
        "customers.services.profile.requests.post",
        side_effect=mocked_response_profile(count=0, data=data),
    ):
        executed = superuser_api_client.execute(
            SEND_EXISTING_INVOICES_MUTATION, input=variables,
        )

    result = executed["data"]["sendExistingBerthInvoices"]["result"]
    assert len(result.get("successful_orders")) == 0
    assert len(result.get("failed_orders")) == 1
    assert len(result.get("failed_leases")) == 0

    failed_order = result.get("failed_orders")[0]
    assert from_global_id(failed_order.get("id"))[0] == "OrderNode"
    assert failed_order.get("error") == "Missing customer email"


@freeze_time("2020-01-01T08:00:00Z")
def test_send_berth_invoices_failed_lease(
    superuser_api_client, notification_template_orders_approved
):
    lease = BerthLeaseFactory(
        renew_automatically=True,
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_season_start_date(today() - relativedelta(years=1)),
        end_date=calculate_season_end_date(today() - relativedelta(years=1)),
    )
    customer = lease.customer

    user = UserFactory()

    # Add the tokens to the headers
    superuser_api_client.execute_options["context"].META[
        "HTTP_API_TOKENS"
    ] = f'{{"{PROFILE_TOKEN_SERVICE}": "token"}}'

    data = {
        "id": to_global_id(ProfileNode, customer.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "primary_email": {"email": user.email},
    }

    assert Order.objects.count() == 0

    variables = {"dueDate": "2020-01-31"}

    with mock.patch(
        "customers.services.profile.requests.post",
        side_effect=mocked_response_profile(count=0, data=data),
    ):
        executed = superuser_api_client.execute(
            SEND_EXISTING_INVOICES_MUTATION, input=variables,
        )

    result = executed["data"]["sendExistingBerthInvoices"]["result"]
    assert len(result.get("successful_orders")) == 0
    assert len(result.get("failed_orders")) == 0
    assert len(result.get("failed_leases")) == 1

    failed_lease = result.get("failed_leases")[0]
    assert from_global_id(failed_lease.get("id"))[0] == "BerthLeaseNode"
    assert failed_lease.get("error") == "No suitable product found"
