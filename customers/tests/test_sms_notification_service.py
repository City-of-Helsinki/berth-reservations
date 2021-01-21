from unittest import mock

from faker import Faker

from berth_reservations.tests.utils import MockResponse
from customers.services.sms_notification_service import SMSNotificationService


def test_send_message():
    phone = Faker(["fi_FI"]).phone_number()
    message = "Test message"
    mock_response = {
        "errors": [],
        "warnings": [],
        "messages": {
            str(phone): {
                "converted": str(phone),
                "status": "SEND",
                "reason": None,
                "messageId": 1,
            }
        },
    }

    with mock.patch(
        "customers.services.profile.requests.post",
        side_effect=lambda *args, **kwargs: MockResponse(mock_response),
    ) as mock_exec:
        response = SMSNotificationService(token="fake_token").send(
            phone_number=phone, message=message
        )

        params = {
            "json": {
                "sender": "Hel.fi",
                "to": [{"destination": phone, "format": "MOBILE"}],
                "text": message,
            },
            "headers": {"Authorization": "Token fake_token"},
        }
        mock_exec.assert_called_with(
            "https://notification-service-api.test.kuva.hel.ninja/v1/message/send",
            **params
        )

    assert response.json() == mock_response
