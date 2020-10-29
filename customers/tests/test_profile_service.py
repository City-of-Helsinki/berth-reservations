from unittest import mock
from uuid import uuid4

from django.test import RequestFactory
from faker import Faker

from customers.schema import ProfileNode
from customers.services.profile import ProfileService
from utils.relay import to_global_id

from .conftest import mocked_response_profile

PROFILE_TOKEN_SERVICE = "http://fake-profile-api.com"


def test_get_city_profile_token():
    r = RequestFactory().request(
        HTTP_API_TOKENS=f'{{"{PROFILE_TOKEN_SERVICE}": "token"}}'
    )
    service = ProfileService(r)
    assert service.profile_token == "token"


def test_get_all_profiles():
    r = RequestFactory().request(
        HTTP_API_TOKENS=f'{{"{PROFILE_TOKEN_SERVICE}": "token"}}'
    )
    with mock.patch(
        "customers.services.profile.requests.post",
        side_effect=mocked_response_profile(count=5),
    ):
        profiles = ProfileService(r).get_all_profiles()

    assert len(profiles.keys()) == 5
    for id, user_profile in profiles.items():
        assert user_profile.id == id
        assert user_profile.first_name is not None
        assert user_profile.last_name is not None
        assert user_profile.email is not None


def test_get_profile(customer_profile, user):
    r = RequestFactory().request(
        HTTP_API_TOKENS=f'{{"{PROFILE_TOKEN_SERVICE}": "token"}}'
    )
    with mock.patch(
        "customers.services.profile.requests.post",
        side_effect=mocked_response_profile(
            count=0,
            data={
                "id": to_global_id(ProfileNode, customer_profile.id),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "primary_email": {"email": user.email},
            },
            use_edges=False,
        ),
    ):
        profile = ProfileService(r).get_profile(customer_profile.id)

    assert profile.id == customer_profile.id
    assert profile.first_name == user.first_name
    assert profile.last_name == user.last_name
    assert profile.email == user.email


def test_parse_user_edge():
    faker = Faker()
    r = RequestFactory().request(
        HTTP_API_TOKENS=f'{{"{PROFILE_TOKEN_SERVICE}": "token"}}'
    )

    user_id = uuid4()
    email = faker.email()
    edge = {
        "node": {
            "id": to_global_id(ProfileNode, user_id),
            "first_name": faker.first_name(),
            "last_name": faker.last_name(),
            "primary_email": {"email": email},
        }
    }

    user = ProfileService(r).parse_user_edge(edge)
    assert user.id == user_id
    assert user.first_name == edge.get("node").get("first_name")
    assert user.last_name == edge.get("node").get("last_name")
    assert user.email == email
