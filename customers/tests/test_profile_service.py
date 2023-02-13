from unittest import mock
from uuid import UUID, uuid4

from faker import Faker

from customers.schema import ProfileNode
from customers.services.profile import ProfileService
from utils.relay import from_global_id, to_global_id

from .conftest import (
    get_customer_profile_dict,
    mocked_response_my_profile,
    mocked_response_profile,
)


@pytest.mark.skip(
    reason="temporarily disabled so that retry logic can be tested in test env"
)
def test_get_all_profiles():
    with mock.patch(
        "customers.services.profile.requests.session.post",
        side_effect=mocked_response_profile(count=5),
    ):
        profiles = ProfileService(profile_token="token").get_all_profiles()

    assert len(profiles.keys()) == 5
    for id, user_profile in profiles.items():
        assert user_profile.id == id
        assert user_profile.first_name is not None
        assert user_profile.last_name is not None
        assert user_profile.email is not None
        assert user_profile.phone is not None


@pytest.mark.skip(
    reason="temporarily disabled so that retry logic can be tested in test env"
)
def test_get_all_profiles_id_list():
    profiles = [get_customer_profile_dict() for _i in range(0, 5)]
    profile_ids = [UUID(from_global_id(profile["id"])) for profile in profiles]

    with mock.patch(
        "customers.services.profile.requests.session.post",
        side_effect=mocked_response_profile(data=profiles, count=0),
    ):
        profiles = ProfileService(profile_token="token").get_all_profiles(
            profile_ids=profile_ids
        )

    assert len(profiles.keys()) == 5
    for id, user_profile in profiles.items():
        assert user_profile.id == id
        assert user_profile.id in profile_ids
        assert user_profile.first_name is not None
        assert user_profile.last_name is not None
        assert user_profile.email is not None
        assert user_profile.phone is not None


@pytest.mark.skip(
    reason="temporarily disabled so that retry logic can be tested in test env"
)
def test_get_profile(customer_profile, user, hki_profile_address):
    faker = Faker()
    phone = faker.phone_number()
    with mock.patch(
        "customers.services.profile.requests.session.post",
        side_effect=mocked_response_profile(
            count=0,
            data={
                "id": to_global_id(ProfileNode, customer_profile.id),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "primary_email": {"email": user.email},
                "primary_phone": {"phone": phone},
                "primary_address": hki_profile_address,
            },
            use_edges=False,
        ),
    ):
        profile = ProfileService(profile_token="token").get_profile(customer_profile.id)

    assert profile.id == customer_profile.id
    assert profile.first_name == user.first_name
    assert profile.last_name == user.last_name
    assert profile.email == user.email
    assert profile.phone == phone
    assert profile.address == hki_profile_address.get("address")
    assert profile.postal_code == hki_profile_address.get("postal_code")
    assert profile.city == hki_profile_address.get("city")


@pytest.mark.skip(
    reason="temporarily disabled so that retry logic can be tested in test env"
)
def test_get_my_profile(customer_profile, user, hki_profile_address):
    faker = Faker()
    phone = faker.phone_number()
    with mock.patch(
        "customers.services.profile.requests.session.post",
        side_effect=mocked_response_my_profile(
            data={
                "id": to_global_id(ProfileNode, customer_profile.id),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "primary_email": {"email": user.email},
                "primary_phone": {"phone": phone},
                "primary_address": hki_profile_address,
            },
        ),
    ):
        profile = ProfileService(profile_token="token").get_my_profile()

    assert profile.id == customer_profile.id
    assert profile.first_name == user.first_name
    assert profile.last_name == user.last_name
    assert profile.email == user.email
    assert profile.phone == phone
    assert profile.address == hki_profile_address.get("address")
    assert profile.postal_code == hki_profile_address.get("postal_code")
    assert profile.city == hki_profile_address.get("city")


def test_parse_user_edge(hki_profile_address):
    faker = Faker()

    user_id = uuid4()
    email = faker.email()
    phone = faker.phone_number()

    edge = {
        "node": {
            "id": to_global_id(ProfileNode, user_id),
            "first_name": faker.first_name(),
            "last_name": faker.last_name(),
            "primary_email": {"email": email},
            "primary_phone": {"phone": phone},
            "primary_address": hki_profile_address,
        }
    }

    user = ProfileService(profile_token="token").parse_user_edge(edge)
    assert user.id == user_id
    assert user.first_name == edge.get("node").get("first_name")
    assert user.last_name == edge.get("node").get("last_name")
    assert user.email == email
    assert user.address == hki_profile_address.get("address")
    assert user.postal_code == hki_profile_address.get("postal_code")
    assert user.city == hki_profile_address.get("city")


def test_parse_user_edge_no_address():
    faker = Faker()

    user_id = uuid4()
    email = faker.email()
    phone = faker.phone_number()

    edge = {
        "node": {
            "id": to_global_id(ProfileNode, user_id),
            "first_name": faker.first_name(),
            "last_name": faker.last_name(),
            "primary_email": {"email": email},
            "primary_phone": {"phone": phone},
            "primary_address": None,
        }
    }

    user = ProfileService(profile_token="token").parse_user_edge(edge)
    assert user.id == user_id
    assert user.first_name == edge.get("node").get("first_name")
    assert user.last_name == edge.get("node").get("last_name")
    assert user.email == email
    assert user.phone == phone
    assert user.address is None
    assert user.postal_code is None
    assert user.city is None
