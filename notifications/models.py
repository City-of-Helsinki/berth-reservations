import logging

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from enumfields import EnumField
from parler.models import TranslatableModel, TranslatedFields

from notifications.enums import NotificationType

logger = logging.getLogger(__name__)


class NotificationTemplateException(Exception):
    pass


class NotificationTemplate(TranslatableModel):
    NOTIFICATION_TYPE_CHOICES = (
        (NotificationType.RESERVATION_CREATED, _('Reservation created')),
    )

    type = EnumField(NotificationType, max_length=50, verbose_name=_('type'), unique=True)

    from_email = models.EmailField(verbose_name=_('From email'), max_length=100, default="dev@hel.fi")

    admins_to_notify = models.ManyToManyField(
        get_user_model(), related_name='+',
        blank=True, verbose_name=_('Admins to notify'),
        help_text=_('Choose admin users you want to be notified when this event happens.'),
    )
    admin_notification_subject = models.CharField(
        verbose_name=_('admin notification subject'),
        max_length=200, help_text=_("Subject for admins' notification"),
        blank=True,
    )
    admin_notification_text = models.TextField(
        verbose_name=_('admin notification text'),
        help_text=_("Text body for admins' notification."),
        blank=True,
    )

    translations = TranslatedFields(
        subject=models.CharField(
            verbose_name=_('subject'), max_length=200, help_text=_('Subject for email notifications')
        ),
        html_body=models.TextField(verbose_name=_('HTML body'), help_text=_('HTML body for email notifications')),
        text_body=models.TextField(
            verbose_name=_('text body'),
            help_text=_('Text body for email notifications. If left blank, HTML body without HTML tags will be used.'),
            blank=True,
        ),
    )

    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')

    def __str__(self):
        for t in self.NOTIFICATION_TYPE_CHOICES:
            if t[0] == self.type:
                return str(t[1])
        return 'N/A'
