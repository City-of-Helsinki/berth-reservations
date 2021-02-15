import environ
from django.conf import settings

from .profile import HelsinkiProfileUser, ProfileService
from .sms_notification_service import SMSNotificationService


def _load_config(template: dict) -> dict:
    config = {}
    env = environ.Env(**template)
    for key in template.keys():
        if hasattr(settings, key):
            config[key] = getattr(settings, key)
        else:
            config[key] = env(key)
    return config


def load_services_config():
    """Initialize the active Profile service config dict
    Also verifies that all config params the service requires are present"""

    # The service tells what keys and types it requires for configuration
    # and the corresponding data has to be set in .env

    for service in [
        ProfileService,
        SMSNotificationService,
    ]:
        template = service.get_config_template()
        service.config = _load_config(template)


__all__ = [
    "HelsinkiProfileUser",
    "ProfileService",
    "SMSNotificationService",
    "load_services_config",
]
