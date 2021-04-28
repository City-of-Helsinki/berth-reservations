import datetime
from unittest import mock

import pytest
from django.core import mail
from freezegun import freeze_time

from applications.enums import ApplicationStatus
from berth_reservations.tests.factories import CustomerProfileFactory
from berth_reservations.tests.utils import assert_not_enough_permissions
from customers.services import SMSNotificationService
from customers.tests.conftest import mocked_response_profile
from payments.notifications import NotificationType
from payments.schema.types import BerthSwitchOfferNode
from utils.relay import to_global_id

from ..enums import OfferStatus
from .conftest import ProfileNode

SEND_BERTH_SWITCH_OFFER_MUTATION = """
mutation SEND_BERTH_SWITCH_OFFER_MUTATION($input: SendBerthSwitchOfferMutationInput!) {
    sendBerthSwitchOffer(input: $input) {
        failedOffers {
            id
            error
        }
        sentOffers
    }
}"""


@freeze_time("2020-10-01T08:00:00Z")
@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
@pytest.mark.parametrize(
    "offer_has_contact_info", [True, False],
)
@pytest.mark.parametrize(
    "profile_token", [None, "dummy_token"],
)
@pytest.mark.parametrize("offer_status", [OfferStatus.DRAFTED, OfferStatus.OFFERED])
def test_send_berth_switch_offer(
    api_client,
    berth_switch_offer,
    offer_has_contact_info,
    profile_token,
    offer_status,
    notification_template_switch_offer_sent,
):
    berth_switch_offer.status = offer_status
    offer_original_email = "test@kuva.hel.ninja"
    offer_original_phone = "+358505658789"
    berth_switch_offer.due_date = datetime.date(2020, 11, 1)
    if offer_has_contact_info:
        berth_switch_offer.customer_phone = offer_original_phone
        berth_switch_offer.customer_email = offer_original_email
    else:
        berth_switch_offer.customer_phone = ""  # trigger update from profile service
        berth_switch_offer.customer_email = ""
    berth_switch_offer.save()

    # set a valid initial status for application
    berth_switch_offer.application.status = (
        ApplicationStatus.PENDING
        if offer_status == OfferStatus.DRAFTED
        else ApplicationStatus.OFFER_SENT
    )
    berth_switch_offer.application.save()

    offers = [berth_switch_offer]

    variables = {
        "offers": [to_global_id(BerthSwitchOfferNode, o.id) for o in offers],
        "dueDate": "2020-01-31",
    }
    if profile_token:
        variables["profileToken"] = profile_token

    customer_profile = CustomerProfileFactory()

    profile_email = "email_stored_in_profile@kuva.hel.ninja"
    profile_phone = "+358404192519"
    profile_data = {
        "id": to_global_id(ProfileNode, customer_profile.id),
        "first_name": berth_switch_offer.application.first_name,
        "last_name": berth_switch_offer.application.last_name,
        "primary_email": {"email": profile_email},
        "primary_phone": {"phone": profile_phone},
    }

    with mock.patch(
        "requests.post",
        side_effect=mocked_response_profile(
            count=0, data=profile_data, use_edges=False
        ),
    ), mock.patch.object(
        SMSNotificationService, "send", return_value=None
    ) as mock_send_sms:
        executed = api_client.execute(SEND_BERTH_SWITCH_OFFER_MUTATION, input=variables)

    if profile_token or offer_has_contact_info:
        # there was sufficient customer info available for sending the offer
        assert executed["data"]["sendBerthSwitchOffer"]["failedOffers"] == []
        assert executed["data"]["sendBerthSwitchOffer"]["sentOffers"] == [
            str(berth_switch_offer.id)
        ]

        berth_switch_offer.refresh_from_db()

        assert berth_switch_offer.status == OfferStatus.OFFERED
        assert berth_switch_offer.application.status == ApplicationStatus.OFFER_SENT

        assert len(mail.outbox) == 1
        assert (
            mail.outbox[0].subject
            == f"test offer sent subject, event: {berth_switch_offer.pk}!"
        )
        assert str(berth_switch_offer.pk) in mail.outbox[0].body

        if profile_token:
            # always when profile_token is supplied, fetch customer info from profile
            assert mail.outbox[0].to == [profile_email]
        else:
            assert mail.outbox[0].to == [offer_original_email]

        assert str(berth_switch_offer.pk) in mail.outbox[0].alternatives[0][0]
        assert mail.outbox[0].alternatives[0][1] == "text/html"

        accept_url = f"https://front-end-url/fi/offer?offer_number={berth_switch_offer.offer_number}&accept=true"
        cancel_url = f"https://front-end-url/fi/offer?offer_number={berth_switch_offer.offer_number}&accept=false"
        mock_send_sms.assert_called_with(
            NotificationType.SMS_BERTH_SWITCH_NOTICE,
            {
                "subject": "Berth switch offer approved",
                "offer": berth_switch_offer,
                "accept_url": accept_url,
                "cancel_url": cancel_url,
                "due_date": "31.1.2020",
            },
            profile_phone if profile_token else offer_original_phone,
            language="fi",
        )
    else:
        # no profile_token and no contact info
        assert len(executed["data"]["sendBerthSwitchOffer"]["failedOffers"]) == 1
        assert (
            "Profile token is required"
            in executed["data"]["sendBerthSwitchOffer"]["failedOffers"][0]["error"]
        )
        assert executed["data"]["sendBerthSwitchOffer"]["sentOffers"] == []
        # Assert that the SMS is not sent
        mock_send_sms.assert_not_called()


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbor_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_send_berth_switch_offer_not_enough_permissions(api_client, berth_switch_offer):
    berth_switch_offer.status = OfferStatus.DRAFTED
    berth_switch_offer.save()
    offers = [berth_switch_offer]

    variables = {
        "offers": [to_global_id(BerthSwitchOfferNode, o.id) for o in offers],
        "dueDate": "2020-01-31",
    }
    executed = api_client.execute(SEND_BERTH_SWITCH_OFFER_MUTATION, input=variables)

    assert_not_enough_permissions(executed)


@freeze_time("2020-01-01T08:00:00Z")
def test_send_berth_switch_offer_non_existent_offer(superuser_api_client, berth):
    variables = {
        "offers": to_global_id(
            BerthSwitchOfferNode, "5b8e89e1-97f5-4827-b0a5-45522ace2d00"
        ),
    }

    executed = superuser_api_client.execute(
        SEND_BERTH_SWITCH_OFFER_MUTATION, input=variables
    )

    assert (
        executed["data"]["sendBerthSwitchOffer"]["failedOffers"][0]["error"]
        == "BerthSwitchOffer matching query does not exist."
    )
