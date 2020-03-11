import pytest

from berth_reservations.tests.conftest import *  # noqa
from harbors.tests.conftest import *  # noqa
from harbors.tests.factories import HarborFactory
from users.tests.conftest import *  # noqa

from ..models import BerthSwitch, BerthSwitchReason
from .factories import BerthApplicationFactory


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
