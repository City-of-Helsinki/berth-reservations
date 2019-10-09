import pytest
from django.core import mail
from django_ilmoitin.models import NotificationTemplate

from ..notifications import NotificationType
from ..signals import reservation_saved
from .factories import BerthReservationFactory, WinterStorageReservationFactory


@pytest.fixture
def notification_template_berth_reservation_created():
    return NotificationTemplate.objects.language("fi").create(
        type=NotificationType.BERTH_RESERVATION_CREATED.value,
        subject="test berth reservation created subject, event: {{ reservation.first_name }}!",
        body_html="<b>test berth reservation created body HTML!</b>",
        body_text="test berth reservation created body text!",
    )


@pytest.fixture
def notification_template_winter_reservation_created():
    return NotificationTemplate.objects.language("fi").create(
        type=NotificationType.WINTER_STORAGE_RESERVATION_CREATED.value,
        subject="test winter reservation created subject, event: {{ reservation.first_name }}!",
        body_html="<b>test winter reservation created body HTML!</b>",
        body_text="test winter reservation created body text!",
    )


def test_berth_reservation_created_notification_is_sent(
    notification_template_berth_reservation_created
):
    reservation = BerthReservationFactory()
    reservation_saved.send(sender="CreateBerthReservation", reservation=reservation)

    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.subject == "test berth reservation created subject, event: {}!".format(
        reservation.first_name
    )


def test_winter_reservation_created_notification_is_sent(
    notification_template_winter_reservation_created
):
    reservation = WinterStorageReservationFactory()
    reservation_saved.send(
        sender="CreateWinterStorageReservation", reservation=reservation
    )

    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.subject == "test winter reservation created subject, event: {}!".format(
        reservation.first_name
    )
