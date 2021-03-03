from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class NotificationType(TextChoices):
    BERTH_APPLICATION_CREATED = (
        "berth_application_created",
        _("Berth application created"),
    )
    BERTH_APPLICATION_REJECTED = (
        "berth_application_rejected",
        _("Berth application rejected"),
    )
    WINTER_STORAGE_APPLICATION_CREATED = (
        "winter_storage_application_created",
        _("Winter storage application created"),
    )
    UNMARKED_WINTER_STORAGE_APPLICATION_CREATED = (
        "unmarked_winter_storage_application_created",
        _("Unmarked winter storage application created"),
    )
