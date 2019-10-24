from django.apps import AppConfig


class ReservationsConfig(AppConfig):
    name = "reservations"

    def ready(self):
        import reservations.notifications  # noqa
        import reservations.signals  # noqa
