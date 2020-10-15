import pytest

from berth_reservations.tests.conftest import *  # noqa
from berth_reservations.tests.factories import CustomerProfileFactory
from harbors.tests.conftest import *  # noqa
from harbors.tests.factories import HarborFactory
from users.tests.conftest import *  # noqa

from ..enums import ApplicationStatus
from ..models import BerthSwitch, BerthSwitchReason
from .factories import BerthApplicationFactory, WinterStorageApplicationFactory


@pytest.fixture
def berth_switch_info(request):
    has_reason = request.param if hasattr(request, "param") else None

    harbor = HarborFactory()
    harbor.create_translation("fi", name="Nykyinen satama")

    berth_switch_reason = (
        BerthSwitchReason.objects.language("fi").create(title="Good reason")
        if has_reason
        else None
    )

    berth_switch = BerthSwitch.objects.create(
        harbor=harbor, pier="D", berth_number="11", reason=berth_switch_reason
    )
    return berth_switch


@pytest.fixture
def berth_switch_reason():
    berth_switch_reason = BerthSwitchReason.objects.language("en").create(
        title="Good reason"
    )
    return berth_switch_reason


@pytest.fixture
def berth_application():
    berth_application = BerthApplicationFactory()
    return berth_application


@pytest.fixture
def berth_application_with_customer(berth_application):
    berth_application.customer = CustomerProfileFactory()
    berth_application.save()
    return berth_application


@pytest.fixture
def winter_storage_application():
    winter_storage_application = WinterStorageApplicationFactory()
    return winter_storage_application


@pytest.fixture
def winter_storage_application_with_customer(winter_storage_application):
    winter_storage_application.customer = CustomerProfileFactory()
    winter_storage_application.save()
    return winter_storage_application


@pytest.fixture
def handled_ws_application(winter_storage_application):
    winter_storage_application.status = ApplicationStatus.HANDLED
    winter_storage_application.save()
    return winter_storage_application
