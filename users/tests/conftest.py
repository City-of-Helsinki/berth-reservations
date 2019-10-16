import pytest

from berth_reservations.tests.conftest import *  # noqa

from .factories import UserFactory


@pytest.fixture
def user():
    return UserFactory()
