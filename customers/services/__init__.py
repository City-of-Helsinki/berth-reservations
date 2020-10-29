import environ
from django.conf import settings

from .profile import HelsinkiProfileUser, ProfileService


def load_services_config():
    """Initialize the active Profile service config dict
    Also verifies that all config params the service requires are present"""

    # The service tells what keys and types it requires for configuration
    # and the corresponding data has to be set in .env
    template = ProfileService.get_config_template()
    env = environ.Env(**template)

    config = {}
    for key in template.keys():
        if hasattr(settings, key):
            config[key] = getattr(settings, key)
        else:
            config[key] = env(key)

    ProfileService.config = config


__all__ = [
    "HelsinkiProfileUser",
    "ProfileService",
    "load_services_config",
]
