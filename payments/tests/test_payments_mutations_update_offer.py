import datetime
import uuid

import pytest
from freezegun import freeze_time

from applications.enums import ApplicationStatus
from applications.new_schema import BerthApplicationNode
from berth_reservations.tests.utils import (
    assert_doesnt_exist,
    assert_not_enough_permissions,
)
from customers.schema import ProfileNode
from leases.enums import LeaseStatus
from leases.schema import BerthLeaseNode
from resources.schema import BerthNode
from utils.relay import to_global_id

from ..enums import OfferStatus
from ..models import BerthSwitchOffer
from ..schema.types import BerthSwitchOfferNode

UPDATE_OFFER_MUTATION = """
mutation UPDATE_OFFER($input: UpdateBerthSwitchOfferMutationInput!) {
    updateBerthSwitchOffer(input: $input) {
        berthSwitchOffer {
            id
            offerNumber
            dueDate
            status
            customerFirstName
            customerLastName
            customer {
                id
            }
            berth {
                id
            }
            application {
                id
                status
            }
            lease {
                id
            }
        }
    }
}
"""


@freeze_time("2021-01-01T08:00:00Z")
@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
@pytest.mark.parametrize(
    "initial_offer_status, initial_application_status, offer_status, expected_application_status",
    [
        (
            OfferStatus.OFFERED,
            ApplicationStatus.OFFER_SENT,
            OfferStatus.CANCELLED,
            ApplicationStatus.OFFER_SENT,
        ),
        (
            OfferStatus.DRAFTED,
            ApplicationStatus.OFFER_GENERATED,
            OfferStatus.CANCELLED,
            ApplicationStatus.OFFER_GENERATED,
        ),
        (
            OfferStatus.OFFERED,
            ApplicationStatus.OFFER_SENT,
            OfferStatus.EXPIRED,
            ApplicationStatus.EXPIRED,
        ),
    ],
)
@pytest.mark.parametrize("due_date", [datetime.date(2021, 1, 31), None])
def test_set_offer_status(
    berth_switch_offer,
    api_client,
    initial_offer_status,
    initial_application_status,
    offer_status,
    expected_application_status,
    due_date,
):
    if initial_offer_status == OfferStatus.DRAFTED:
        berth_switch_offer.due_date = None
    else:
        berth_switch_offer.due_date = datetime.date(2021, 1, 15)
    berth_switch_offer.status = initial_offer_status
    berth_switch_offer.save()
    berth_switch_offer.application.status = initial_application_status
    berth_switch_offer.application.save()

    global_id = to_global_id(BerthSwitchOfferNode, berth_switch_offer.id)

    variables = {
        "id": global_id,
        "status": offer_status.name,
    }
    if due_date:
        variables["dueDate"] = due_date

    assert BerthSwitchOffer.objects.count() == 1

    executed = api_client.execute(UPDATE_OFFER_MUTATION, input=variables)

    assert BerthSwitchOffer.objects.count() == 1

    expected_due_date = None
    if due_date:
        expected_due_date = str(due_date)
    elif berth_switch_offer.due_date:
        expected_due_date = str(berth_switch_offer.due_date)

    assert executed["data"]["updateBerthSwitchOffer"]["berthSwitchOffer"] == {
        "id": variables["id"],
        "status": offer_status.name,
        "dueDate": expected_due_date,
        "offerNumber": berth_switch_offer.offer_number,
        "customerFirstName": berth_switch_offer.customer_first_name,
        "customerLastName": berth_switch_offer.customer_last_name,
        "customer": {"id": to_global_id(ProfileNode, berth_switch_offer.customer.id)},
        "berth": {"id": to_global_id(BerthNode, berth_switch_offer.berth.id)},
        "application": {
            "id": to_global_id(BerthApplicationNode, berth_switch_offer.application.id),
            "status": expected_application_status.name,
        },
        "lease": {"id": to_global_id(BerthLeaseNode, berth_switch_offer.lease.id)},
    }
    berth_switch_offer.refresh_from_db()
    berth_switch_offer.lease.refresh_from_db()
    assert berth_switch_offer.log_entries.count() == 1
    log_entry = berth_switch_offer.log_entries.first()
    assert log_entry.to_status == str(offer_status)
    assert "Manually updated by admin" in log_entry.comment
    assert berth_switch_offer.lease.status == LeaseStatus.PAID


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_update_order_not_enough_permissions(api_client):
    variables = {
        "id": to_global_id(BerthSwitchOfferNode, uuid.uuid4()),
    }

    assert BerthSwitchOffer.objects.count() == 0

    executed = api_client.execute(UPDATE_OFFER_MUTATION, input=variables)

    assert BerthSwitchOffer.objects.count() == 0
    assert_not_enough_permissions(executed)


def test_update_offer_does_not_exist(superuser_api_client):
    variables = {
        "id": to_global_id(BerthSwitchOfferNode, uuid.uuid4()),
    }
    executed = superuser_api_client.execute(UPDATE_OFFER_MUTATION, input=variables)

    assert_doesnt_exist("BerthSwitchOffer", executed)
