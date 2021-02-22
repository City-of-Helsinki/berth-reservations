import pytest
from django_ilmoitin.models import NotificationTemplate

from applications.tests.conftest import *  # noqa
from berth_reservations.tests.conftest import *  # noqa
from customers.tests.conftest import *  # noqa
from customers.tests.factories import BoatFactory
from resources.tests.conftest import *  # noqa

from ..notifications import NotificationType
from ..stickers import create_ws_sticker_sequences
from .factories import BerthLeaseFactory, WinterStorageLeaseFactory


@pytest.fixture
def sticker_sequences():
    create_ws_sticker_sequences()


@pytest.fixture
def berth_lease():
    boat = BoatFactory()
    return BerthLeaseFactory(customer=boat.owner, boat=boat)


@pytest.fixture
def winter_storage_lease():
    boat = BoatFactory()
    return WinterStorageLeaseFactory(customer=boat.owner, boat=boat)


@pytest.fixture
def notification_template_berth_lease_terminated():
    return NotificationTemplate.objects.language("fi").create(
        type=NotificationType.BERTH_LEASE_TERMINATED_LEASE_NOTICE,
        subject="test berth lease rejected subject",
        body_html="<b>test berth lease terminated</b> {{ cancelled_at }} {{ lease.id }}",
        body_text="test berth lease terminated {{ cancelled_at }} {{ lease.id }}",
    )


@pytest.fixture
def notification_template_ws_lease_terminated():
    return NotificationTemplate.objects.language("fi").create(
        type=NotificationType.WINTER_STORAGE_LEASE_TERMINATED_LEASE_NOTICE,
        subject="test ws lease rejected subject",
        body_html="<b>test ws lease terminated</b> {{ cancelled_at }} {{ lease.id }}",
        body_text="test ws lease terminated {{ cancelled_at }} {{ lease.id }}",
    )
