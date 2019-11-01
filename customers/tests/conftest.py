import pytest

from berth_reservations.tests.conftest import *  # noqa

from .factories import CustomerProfileFactory


@pytest.fixture
def customer_profile():
    return CustomerProfileFactory()
