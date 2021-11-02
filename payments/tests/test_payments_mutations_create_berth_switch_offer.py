from random import randint
from unittest import mock
from uuid import uuid4

import pytest
from faker import Faker
from freezegun import freeze_time

from applications.schema import BerthApplicationNode
from applications.tests.factories import BerthSwitchFactory
from berth_reservations.tests.utils import (
    assert_doesnt_exist,
    assert_in_errors,
    assert_not_enough_permissions,
)
from customers.tests.conftest import mocked_response_profile
from leases.enums import LeaseStatus
from leases.schema import BerthLeaseNode
from leases.tests.factories import BerthLeaseFactory
from leases.utils import calculate_season_end_date, calculate_season_start_date
from resources.schema import BerthNode
from resources.tests.factories import BerthFactory
from utils.relay import to_global_id

from ..enums import OfferStatus
from .conftest import ProfileNode

CREATE_BERTH_SWITCH_OFFER_MUTATION = """
mutation CREATE_BERTH_SWITCH_OFFER_MUTATION($input: CreateBerthSwitchOfferMutationInput!) {
    createBerthSwitchOffer(input: $input) {
        berthSwitchOffer {
            status
            dueDate
            customer {
                id
            }
            application {
                id
                status
            }
            lease {
                id
            }
            berth {
                id
            }
        }
    }
}"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_services"],
    indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_create_berth_switch_offer(api_client, berth_application, berth):
    berth_lease = BerthLeaseFactory(
        start_date=calculate_season_start_date(),
        end_date=calculate_season_end_date(),
        status=LeaseStatus.PAID,
    )
    berth_application.customer = berth_lease.customer
    berth_application.berth_switch = BerthSwitchFactory(berth=berth_lease.berth)
    berth_application.save()
    berth_lease.save()

    variables = {
        "applicationId": to_global_id(BerthApplicationNode, berth_application.id),
        "newBerthId": to_global_id(BerthNode, berth.id),
    }
    executed = api_client.execute(CREATE_BERTH_SWITCH_OFFER_MUTATION, input=variables)

    assert executed["data"]["createBerthSwitchOffer"]["berthSwitchOffer"] == {
        "status": OfferStatus.DRAFTED.name,
        "dueDate": None,
        "application": {"id": variables["applicationId"], "status": "OFFER_GENERATED"},
        "customer": {"id": to_global_id(ProfileNode, berth_lease.customer.id)},
        "lease": {"id": to_global_id(BerthLeaseNode, berth_lease.id)},
        "berth": {"id": variables["newBerthId"]},
    }


@pytest.mark.parametrize(
    "api_client",
    ["berth_services"],
    indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_create_berth_switch_offer_old_lease(api_client, berth_application, berth):
    berth_lease = BerthLeaseFactory(
        start_date=calculate_season_start_date(),
        end_date=calculate_season_end_date(),
        status=LeaseStatus.PAID,
    )
    BerthLeaseFactory(
        customer=berth_lease.customer,
        start_date=calculate_season_start_date(),
        end_date=calculate_season_end_date(),
        status=LeaseStatus.PAID,
    )
    berth_application.customer = berth_lease.customer
    berth_application.berth_switch = BerthSwitchFactory(berth=berth_lease.berth)
    berth_application.save()

    variables = {
        "applicationId": to_global_id(BerthApplicationNode, berth_application.id),
        "newBerthId": to_global_id(BerthNode, berth.id),
        "oldLeaseId": to_global_id(BerthLeaseNode, berth_lease.id),
    }
    executed = api_client.execute(CREATE_BERTH_SWITCH_OFFER_MUTATION, input=variables)

    assert executed["data"]["createBerthSwitchOffer"]["berthSwitchOffer"] == {
        "status": OfferStatus.DRAFTED.name,
        "dueDate": None,
        "application": {"id": variables["applicationId"], "status": "OFFER_GENERATED"},
        "customer": {"id": to_global_id(ProfileNode, berth_lease.customer.id)},
        "lease": {"id": to_global_id(BerthLeaseNode, berth_lease.id)},
        "berth": {"id": variables["newBerthId"]},
    }


@pytest.mark.parametrize(
    "api_client",
    ["berth_services"],
    indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_create_berth_switch_offer_wrong_berth(api_client, berth_application, berth):
    berth_lease = BerthLeaseFactory(
        start_date=calculate_season_start_date(),
        end_date=calculate_season_end_date(),
        status=LeaseStatus.PAID,
    )
    berth_application.customer = berth_lease.customer

    berth_application.berth_switch = BerthSwitchFactory(
        berth=BerthFactory(number="9999"),
    )
    berth_application.save()

    variables = {
        "applicationId": to_global_id(BerthApplicationNode, berth_application.id),
        "newBerthId": to_global_id(BerthNode, berth.id),
    }
    executed = api_client.execute(CREATE_BERTH_SWITCH_OFFER_MUTATION, input=variables)

    assert_in_errors("NO_LEASE", executed)


@pytest.mark.parametrize(
    "api_client",
    ["berth_services"],
    indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_create_berth_switch_offer_missing_customer(
    api_client, berth_application, berth
):
    berth_lease = BerthLeaseFactory(
        start_date=calculate_season_start_date(), end_date=calculate_season_end_date()
    )
    berth_application.customer = None
    berth_application.berth_switch = BerthSwitchFactory()
    berth_application.save()

    berth_lease.status = LeaseStatus.PAID
    berth_lease.save()

    variables = {
        "applicationId": to_global_id(BerthApplicationNode, berth_application.id),
        "newBerthId": to_global_id(BerthNode, berth.id),
    }
    executed = api_client.execute(CREATE_BERTH_SWITCH_OFFER_MUTATION, input=variables)
    assert_in_errors("Application must be connected to a customer", executed)


@pytest.mark.parametrize(
    "api_client",
    ["berth_services"],
    indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_create_berth_switch_offer_missing_application_switch(
    api_client, berth_application, berth
):
    berth_lease = BerthLeaseFactory(
        start_date=calculate_season_start_date(), end_date=calculate_season_end_date()
    )
    berth_application.customer = berth_lease.customer
    berth_application.berth_switch = None
    berth_application.save()

    berth_lease.status = LeaseStatus.PAID
    berth_lease.save()

    variables = {
        "applicationId": to_global_id(BerthApplicationNode, berth_application.id),
        "newBerthId": to_global_id(BerthNode, berth.id),
    }
    executed = api_client.execute(CREATE_BERTH_SWITCH_OFFER_MUTATION, input=variables)
    assert_in_errors("Application must be a switch application", executed)


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_create_berth_switch_offer_not_enough_permissions(api_client, order):
    variables = {
        "applicationId": to_global_id(BerthApplicationNode, randint(0, 100)),
        "newBerthId": to_global_id(BerthNode, uuid4()),
    }

    executed = api_client.execute(CREATE_BERTH_SWITCH_OFFER_MUTATION, input=variables)

    assert_not_enough_permissions(executed)


@freeze_time("2020-01-01T08:00:00Z")
def test_create_berth_switch_offer_application_does_not_exist(
    superuser_api_client, berth
):
    variables = {
        "applicationId": to_global_id(BerthApplicationNode, randint(0, 100)),
        "newBerthId": to_global_id(BerthNode, berth.id),
    }

    executed = superuser_api_client.execute(
        CREATE_BERTH_SWITCH_OFFER_MUTATION, input=variables
    )

    assert_doesnt_exist("BerthApplication", executed)


@freeze_time("2020-01-01T08:00:00Z")
def test_create_berth_switch_offer_berth_does_not_exist(
    superuser_api_client, berth_application, customer_profile
):
    berth_application.berth_switch = BerthSwitchFactory()
    berth_application.customer = customer_profile
    berth_application.save()

    variables = {
        "applicationId": to_global_id(BerthApplicationNode, berth_application.id),
        "newBerthId": to_global_id(BerthNode, uuid4()),
    }

    executed = superuser_api_client.execute(
        CREATE_BERTH_SWITCH_OFFER_MUTATION, input=variables
    )

    assert_doesnt_exist("Berth", executed)


@freeze_time("2020-01-01T08:00:00Z")
def test_create_berth_switch_offer_lease_does_not_exist(
    superuser_api_client, berth_application, berth, customer_profile
):
    berth_application.berth_switch = BerthSwitchFactory()
    berth_application.customer = customer_profile
    berth_application.save()

    variables = {
        "applicationId": to_global_id(BerthApplicationNode, berth_application.id),
        "newBerthId": to_global_id(BerthNode, berth.id),
        "oldLeaseId": to_global_id(BerthLeaseNode, uuid4()),
    }

    executed = superuser_api_client.execute(
        CREATE_BERTH_SWITCH_OFFER_MUTATION, input=variables
    )

    assert_doesnt_exist("BerthLease", executed)


CREATE_BERTH_SWITCH_OFFER_MUTATION_CUSTOMER_FIELDS = """
mutation CREATE_BERTH_SWITCH_OFFER_MUTATION($input: CreateBerthSwitchOfferMutationInput!) {
    createBerthSwitchOffer(input: $input) {
        berthSwitchOffer {
            customerFirstName
            customerLastName
            customerEmail
            customerPhone
        }
    }
}"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_services"],
    indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_create_berth_switch_offer_refresh_profile(
    api_client, berth_application, berth
):
    faker = Faker("fi_FI")
    berth_lease = BerthLeaseFactory(
        start_date=calculate_season_start_date(),
        end_date=calculate_season_end_date(),
        status=LeaseStatus.PAID,
    )
    berth_application.customer = berth_lease.customer
    berth_application.berth_switch = BerthSwitchFactory(berth=berth_lease.berth)
    berth_application.save()

    first_name = faker.first_name()
    last_name = faker.last_name()
    email = faker.email()
    phone = faker.phone_number()

    data = {
        "id": to_global_id(ProfileNode, berth_lease.customer.id),
        "first_name": first_name,
        "last_name": last_name,
        "primary_email": {"email": email},
        "primary_phone": {"phone": phone},
    }
    variables = {
        "applicationId": to_global_id(BerthApplicationNode, berth_application.id),
        "newBerthId": to_global_id(BerthNode, berth.id),
        "profileToken": "profile-token",
    }
    with mock.patch(
        "customers.services.profile.requests.post",
        side_effect=mocked_response_profile(count=0, data=data, use_edges=False),
    ):
        executed = api_client.execute(
            CREATE_BERTH_SWITCH_OFFER_MUTATION_CUSTOMER_FIELDS, input=variables
        )

    assert executed["data"]["createBerthSwitchOffer"]["berthSwitchOffer"] == {
        "customerFirstName": first_name,
        "customerLastName": last_name,
        "customerEmail": email,
        "customerPhone": phone,
    }
