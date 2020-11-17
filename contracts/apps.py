from django.apps import AppConfig


class ContractsConfig(AppConfig):
    name = "contracts"

    def ready(self):
        from .services import load_services_config

        load_services_config()
