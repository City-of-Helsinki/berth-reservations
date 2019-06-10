import pytest

from berth_reservations.tests.conftest import *  # noqa
from harbors.models import Harbor
from harbors.tests.conftest import *  # noqa

from ..models import BerthSwitch


@pytest.fixture
def berth_switch_info():
    harbor = Harbor.objects.language("en").create(name="Current harbor")
    harbor.set_current_language("fi")
    harbor.name = "Nykyinen satama"
    harbor.save()

    berth_switch = BerthSwitch.objects.create(
        harbor=harbor, pier="D", berth_number="11"
    )
    return berth_switch
