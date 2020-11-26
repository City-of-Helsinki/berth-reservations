from django.apps import AppConfig


class CustomersConfig(AppConfig):
    name = "customers"

    def ready(self):
        import customers.signals  # noqa

        from .services import load_services_config

        load_services_config()
