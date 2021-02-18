import requests
from django.conf import settings
from django_ilmoitin.models import NotificationTemplate
from django_ilmoitin.utils import render_notification_template

NOTIFICATION_SERVICE_API_URL = "NOTIFICATION_SERVICE_API_URL"
NOTIFICATION_SERVICE_SENDER_NAME = "NOTIFICATION_SERVICE_SENDER_NAME"
NOTIFICATION_SERVICE_TOKEN = "NOTIFICATION_SERVICE_TOKEN"


DEFAULT_LANGUAGE = settings.LANGUAGE_CODE


class SMSNotificationService:
    """
    The documentation for the API can be found on the GitHub repo:
    https://github.com/City-of-Helsinki/notification-service-api
    """

    def __init__(self, **kwargs):
        if "config" in kwargs:
            self.config = kwargs.get("config")

        self.api_url = self.config.get(NOTIFICATION_SERVICE_API_URL)
        self.sender_name = self.config.get(NOTIFICATION_SERVICE_SENDER_NAME)
        self.token = kwargs.get("token") or self.config.get(NOTIFICATION_SERVICE_TOKEN)
        assert self.token

    @staticmethod
    def get_config_template():
        return {
            NOTIFICATION_SERVICE_API_URL: str,
            NOTIFICATION_SERVICE_SENDER_NAME: str,
            NOTIFICATION_SERVICE_TOKEN: str,
        }

    def send(
        self,
        notification_type: str,
        context: dict,
        phone_number: str,
        language=DEFAULT_LANGUAGE,
    ):
        template = NotificationTemplate.objects.get(type=notification_type)
        message = render_notification_template(template, context, language).body_text
        return self.send_plain_text(phone_number, message)

    def send_plain_text(self, phone_number: str, message: str):
        data = {
            "sender": self.sender_name,
            "to": [{"destination": phone_number, "format": "MOBILE"}],
            "text": message,
        }
        return self._do_send(data)

    def send_batch(self, phone_numbers: list, message: str):
        data = {
            "sender": self.sender_name,
            "to": [
                {"destination": phone_number, "format": "MOBILE"}
                for phone_number in phone_numbers
            ],
            "text": message,
        }
        return self._do_send(data)

    def _do_send(self, data):
        headers = {"Authorization": f"Token {self.token}"}
        return requests.post(f"{self.api_url}/message/send", json=data, headers=headers)
