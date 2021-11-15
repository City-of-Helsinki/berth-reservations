from django.conf import settings
from django.http import HttpRequest
from django.utils.module_loading import import_string

from utils.config import get_config_from_env

from .bambora_payform import BamboraPayformProvider
from .base import PaymentProvider

_provider_class: PaymentProvider

__all__ = [
    "BamboraPayformProvider",
    "get_payment_provider",
]


def load_provider_config():
    """Initialize the active payment provider config dict
    Also verifies that all config params the provider requires are present"""
    global _provider_class

    # Provider path is the only thing loaded from env
    # in the global settings, the rest are added here
    provider_path = settings.VENE_PAYMENTS_PROVIDER_CLASS
    _provider_class = import_string(provider_path)

    # Provider tells what keys and types it requires for configuration
    # and the corresponding data has to be set in .env
    template = _provider_class.get_config_template()

    _provider_class.config = get_config_from_env(template)


def get_payment_provider(
    request: HttpRequest, ui_return_url: str = None
) -> PaymentProvider:
    """Get a new instance of the active payment provider with associated request
    and optional return_url info"""
    global _provider_class

    return _provider_class(request=request, ui_return_url=ui_return_url)
