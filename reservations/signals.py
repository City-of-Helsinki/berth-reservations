from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from notifications.enums import NotificationType
from notifications.utils import send_notification
from .models import Reservation


@receiver(post_save, sender=Reservation)
def reservation_notification_handler(sender, instance, created, **kwargs):
    if created:
        send_notification(instance.email, NotificationType.RESERVATION_CREATED)


if settings.NOTIFICATIONS_ENABLED:
    post_save.connect(reservation_notification_handler, Reservation)
