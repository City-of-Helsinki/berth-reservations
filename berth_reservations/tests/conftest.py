import pytest
from rest_framework.test import APIClient

from .factories import UserFactory


@pytest.fixture(autouse=True)
def autouse_django_db(db):
    pass


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user():
    user = UserFactory()
    user.is_staff = True
    user.save()
    return user
