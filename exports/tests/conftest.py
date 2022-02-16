import pytest
from rest_framework.test import APIClient

from applications.tests.conftest import *  # noqa
from berth_reservations.tests.conftest import *  # noqa
from users.tests.conftest import *  # noqa


@pytest.fixture
def rest_api_client():
    return APIClient()


@pytest.fixture
def user_api_client(rest_api_client, user):
    rest_api_client.force_authenticate(user=user)
    rest_api_client.user = user
    return rest_api_client


@pytest.fixture
def superuser_api_client(rest_api_client, superuser):
    rest_api_client.force_authenticate(user=superuser)
    rest_api_client.user = superuser
    return rest_api_client
