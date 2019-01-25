import pytest
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def autouse_django_db(db):
    pass


@pytest.fixture
def api_client():
    return APIClient()
