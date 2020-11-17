import environ
from django.conf import settings
from django.utils.module_loading import import_string

from .visma_contract import VismaContractService  # noqa


def load_services_config():
    service_class = import_string(settings.VENE_CONTRACTS_SERVICE_CLASS)
    template = service_class.get_config_template()
    env = environ.Env(**template)

    config = {}
    for key in template.keys():
        if hasattr(settings, key):
            config[key] = getattr(settings, key)
        else:
            config[key] = env(key)

    service_class.config = config


def get_contract_service():
    """Get an instance of the contracts service."""
    return import_string(settings.VENE_CONTRACTS_SERVICE_CLASS)()
