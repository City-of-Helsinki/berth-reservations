from unittest import mock

from faker import Faker
from freezegun import freeze_time

from berth_reservations.tests.utils import MockJsonResponse
from customers.services.sms_notification_service import SMSNotificationService
from payments.notifications import NotificationType


def test_send_plain_text_message():
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
        "customers.services.sms_notification_service.requests.post",
        side_effect=lambda *args, **kwargs: MockJsonResponse(mock_response),
    ) as mock_exec:
        notification_service = SMSNotificationService(token="fake_token")
        response = notification_service.send_plain_text(
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
            notification_service.api_url + "/message/send", **params
        )

    assert response.json() == mock_response


@freeze_time("2020-01-01T08:00:00Z")
def test_send_message(notification_template_sms_invoice_notice):
    phone = Faker(["fi_FI"]).phone_number()
    message = "Remember to pay your invoice berth by 15-01-2020"
    notification_type = NotificationType.SMS_INVOICE_NOTICE
    context = {"product_name": "berth", "order": {"due_date": "15-01-2020"}}

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
        "customers.services.sms_notification_service.requests.post",
        side_effect=lambda *args, **kwargs: MockJsonResponse(mock_response),
    ) as mock_exec:
        notification_service = SMSNotificationService(token="fake_token")
        response = notification_service.send(notification_type, context, phone)

        params = {
            "json": {
                "sender": "Hel.fi",
                "to": [{"destination": phone, "format": "MOBILE"}],
                "text": message,
            },
            "headers": {"Authorization": "Token fake_token"},
        }
        mock_exec.assert_called_with(
            notification_service.api_url + "/message/send", **params
        )

    assert response.json() == mock_response
