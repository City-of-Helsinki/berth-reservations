from utils.config import get_config_from_env

from .profile import HelsinkiProfileUser, ProfileService
from .sms_notification_service import SMSNotificationService


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
        service.config = get_config_from_env(template)


__all__ = [
    "HelsinkiProfileUser",
    "ProfileService",
    "SMSNotificationService",
    "load_services_config",
]
