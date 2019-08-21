from django.apps import AppConfig


class ReservationsConfig(AppConfig):
    name = "reservations"

    def __init__(self, *args, **kwargs):
        super(ReservationsConfig, self).__init__(*args, **kwargs)
        import reservations.notifications  # noqa

    def ready(self):
        import reservations.signals  # noqa
