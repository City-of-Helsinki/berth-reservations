from django.apps import AppConfig


class ApplicationsConfig(AppConfig):
    name = "applications"

    def ready(self):
        import applications.notifications  # noqa
        import applications.signals  # noqa
