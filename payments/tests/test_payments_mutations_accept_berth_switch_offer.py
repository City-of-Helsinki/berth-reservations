from datetime import date

import pytest
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from applications.enums import ApplicationStatus
from berth_reservations.tests.factories import CustomerProfileFactory
from berth_reservations.tests.utils import assert_doesnt_exist
from leases.enums import LeaseStatus
from leases.models import BerthLease
from leases.tests.factories import BerthLeaseFactory
from leases.utils import (
    calculate_berth_lease_end_date,
    calculate_berth_lease_start_date,
)
from payments.enums import OfferStatus
from payments.tests.factories import BerthSwitchOfferFactory

# from payments.schema.types import BerthSwitchOfferNode
# from utils.relay import to_global_id

ACCEPT_BERTH_SWITCH_OFFER_MUTATION = """
mutation ACCEPT_BERTH_SWITCH_OFFER_MUTATION($input: AcceptBerthSwitchOfferMutationInput!) {
    acceptBerthSwitchOffer(input: $input) {
        __typename
    }
}
"""


@freeze_time("2020-02-01T08:00:00Z")
def test_accept_offer(user_api_client):
    customer = CustomerProfileFactory()
    due_date = date.today() + relativedelta(days=14)
    berth_switch_offer = BerthSwitchOfferFactory(
        customer=customer,
        due_date=due_date,
        status=OfferStatus.OFFERED,
        lease=BerthLeaseFactory(
            customer=customer,
            start_date=calculate_berth_lease_start_date(),
            end_date=calculate_berth_lease_end_date(),
            status=LeaseStatus.PAID,
        ),
    )

    variables = {
        # "offerId": to_global_id(BerthSwitchOfferNode, berth_switch_offer.id),
        "offerNumber": berth_switch_offer.offer_number,
        "isAccepted": True,
    }

    user_api_client.execute(ACCEPT_BERTH_SWITCH_OFFER_MUTATION, input=variables)

    berth_switch_offer.refresh_from_db()
    berth_switch_offer.lease.refresh_from_db()

    assert berth_switch_offer.status == OfferStatus.ACCEPTED
    assert berth_switch_offer.lease.status == LeaseStatus.TERMINATED
    new_lease = BerthLease.objects.exclude(id=berth_switch_offer.lease_id).first()
    assert new_lease.status == LeaseStatus.PAID
    assert new_lease.application == berth_switch_offer.application


@freeze_time("2020-02-01T08:00:00Z")
def test_reject_offer(user_api_client):
    customer = CustomerProfileFactory()
    due_date = date.today() + relativedelta(days=14)
    berth_switch_offer = BerthSwitchOfferFactory(
        customer=customer,
        due_date=due_date,
        status=OfferStatus.OFFERED,
        lease=BerthLeaseFactory(
            customer=customer,
            start_date=calculate_berth_lease_start_date(),
            end_date=calculate_berth_lease_end_date(),
            status=LeaseStatus.PAID,
        ),
    )

    variables = {
        # "offerId": to_global_id(BerthSwitchOfferNode, berth_switch_offer.id),
        "offerNumber": berth_switch_offer.offer_number,
        "isAccepted": False,
    }

    user_api_client.execute(ACCEPT_BERTH_SWITCH_OFFER_MUTATION, input=variables)

    berth_switch_offer.refresh_from_db()
    berth_switch_offer.lease.refresh_from_db()

    assert berth_switch_offer.status == OfferStatus.REJECTED
    assert berth_switch_offer.lease.status == LeaseStatus.PAID
    assert berth_switch_offer.application.status == ApplicationStatus.REJECTED
    assert BerthLease.objects.all().count() == 1


@freeze_time("2020-02-01T08:00:00Z")
@pytest.mark.parametrize("is_accepted", [True, False])
@pytest.mark.parametrize(
    "initial_status",
    [
        OfferStatus.REJECTED,
        OfferStatus.DRAFTED,
        OfferStatus.CANCELLED,
        OfferStatus.ACCEPTED,
    ],
)
def test_accept_offer_invalid_status(user_api_client, is_accepted, initial_status):
    customer = CustomerProfileFactory()
    due_date = date.today() + relativedelta(days=14)
    berth_switch_offer = BerthSwitchOfferFactory(
        customer=customer,
        due_date=due_date,
        status=initial_status,
        lease=BerthLeaseFactory(
            customer=customer,
            start_date=calculate_berth_lease_start_date(),
            end_date=calculate_berth_lease_end_date(),
            status=LeaseStatus.PAID,
        ),
    )

    variables = {
        # "offerId": to_global_id(BerthSwitchOfferNode, berth_switch_offer.id),
        "offerNumber": berth_switch_offer.offer_number,
        "isAccepted": is_accepted,
    }

    user_api_client.execute(ACCEPT_BERTH_SWITCH_OFFER_MUTATION, input=variables)

    berth_switch_offer.refresh_from_db()
    berth_switch_offer.lease.refresh_from_db()

    assert berth_switch_offer.status == initial_status
    assert berth_switch_offer.lease.status == LeaseStatus.PAID
    new_lease = BerthLease.objects.exclude(id=berth_switch_offer.lease_id).first()
    assert new_lease is None


def test_accept_berth_switch_offer_does_not_exist(user_api_client):
    variables = {
        "offerNumber": "test",
        "isAccepted": True,
    }
    executed = user_api_client.execute(
        ACCEPT_BERTH_SWITCH_OFFER_MUTATION, input=variables
    )

    assert_doesnt_exist("BerthSwitchOffer", executed)
