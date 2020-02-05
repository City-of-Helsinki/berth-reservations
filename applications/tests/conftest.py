import pytest

from berth_reservations.tests.conftest import *  # noqa
from harbors.models import Harbor
from harbors.tests.conftest import *  # noqa
from users.tests.conftest import *  # noqa

from ..models import BerthSwitch, BerthSwitchReason


@pytest.fixture
def berth_switch_info(request):
    has_reason = request.param if hasattr(request, "param") else None

    harbor = Harbor.objects.language("en").create(name="Current harbor")
    harbor.set_current_language("fi")
    harbor.name = "Nykyinen satama"
    harbor.save()

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
