import requests

NOTIFICATION_SERVICE_API_URL = "NOTIFICATION_SERVICE_API_URL"
NOTIFICATION_SERVICE_SENDER_NAME = "NOTIFICATION_SERVICE_SENDER_NAME"
NOTIFICATION_SERVICE_TOKEN = "NOTIFICATION_SERVICE_TOKEN"


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
        self.token = self.config.get(NOTIFICATION_SERVICE_TOKEN)
        assert self.token

    @staticmethod
    def get_config_template():
        return {
            NOTIFICATION_SERVICE_API_URL: str,
            NOTIFICATION_SERVICE_SENDER_NAME: str,
            NOTIFICATION_SERVICE_TOKEN: str,
        }

    def send(self, phone_number: str, message: str):
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
