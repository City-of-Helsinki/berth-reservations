import pytest
from django.core import mail
from django_ilmoitin.models import NotificationTemplate

from ..constants import MARKED_WS_SENDER, REJECT_BERTH_SENDER, UNMARKED_WS_SENDER
from ..notifications import NotificationType
from ..signals import application_rejected, application_saved
from .factories import BerthApplicationFactory, WinterStorageApplicationFactory


@pytest.fixture
def notification_template_berth_application_created():
    return NotificationTemplate.objects.language("fi").create(
        type=NotificationType.BERTH_APPLICATION_CREATED.value,
        subject="test berth application created subject, event: {{ application.first_name }}!",
        body_html="<b>test berth application created body HTML!</b>",
        body_text="test berth application created body text!",
    )


@pytest.fixture
def notification_template_winter_application_created():
    return NotificationTemplate.objects.language("fi").create(
        type=NotificationType.WINTER_STORAGE_APPLICATION_CREATED.value,
        subject="test winter application created subject, event: {{ application.first_name }}!",
        body_html="<b>test winter application created body HTML!</b>",
        body_text="test winter application created body text!",
    )


@pytest.fixture
def notification_template_unmarked_winter_application_created():
    return NotificationTemplate.objects.language("fi").create(
        type=NotificationType.UNMARKED_WINTER_STORAGE_APPLICATION_CREATED.value,
        subject="test unmarked winter application created subject, event: {{ application.first_name }}!",
        body_html="<b>test winter application created body HTML!</b>",
        body_text="test winter application created body text!",
    )


def test_berth_application_created_notification_is_sent(
    notification_template_berth_application_created,
):
    application = BerthApplicationFactory()
    application_saved.send(sender="CreateBerthApplication", application=application)

    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.subject == "test berth application created subject, event: {}!".format(
        application.first_name
    )


def test_berth_application_rejected_notification_is_sent(
    notification_template_berth_application_rejected,
):
    application = BerthApplicationFactory()
    application_rejected.send(sender=REJECT_BERTH_SENDER, application=application)

    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.subject == "test berth application rejected subject, event: {}!".format(
        application.first_name
    )


def test_winter_application_created_notification_is_sent(
    notification_template_winter_application_created,
):
    application = WinterStorageApplicationFactory()
    application_saved.send(sender=MARKED_WS_SENDER, application=application)

    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.subject == "test winter application created subject, event: {}!".format(
        application.first_name
    )


def test_unmarked_winter_application_created_notification_is_sent(
    notification_template_unmarked_winter_application_created,
):
    application = WinterStorageApplicationFactory()
    application_saved.send(sender=UNMARKED_WS_SENDER, application=application)

    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert (
        msg.subject
        == "test unmarked winter application created subject, event: {}!".format(
            application.first_name
        )
    )
