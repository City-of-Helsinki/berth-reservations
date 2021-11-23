from django.conf import settings
from django.utils.module_loading import import_string

from utils.config import get_config_from_env

from .visma_contract import VismaContractService  # noqa


def load_services_config():
    service_class = import_string(settings.VENE_CONTRACTS_SERVICE_CLASS)
    template = service_class.get_config_template()
    service_class.config = get_config_from_env(template)


def get_contract_service():
    """Get an instance of the contracts service."""
    return import_string(settings.VENE_CONTRACTS_SERVICE_CLASS)()
