from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    name = "payments"

    def ready(self):
        import payments.notifications  # noqa

        # Verify active payment provider configuration
        from .providers import load_provider_config

        load_provider_config()
