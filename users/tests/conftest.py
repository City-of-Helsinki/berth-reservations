import pytest

from berth_reservations.tests.conftest import *  # noqa

from .factories import UserFactory


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def admin_user(user):
    user.is_staff = True
    user.save()
    return user


@pytest.fixture
def superuser(user):
    user.is_superuser = True
    user.save()
    return user
