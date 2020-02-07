import pytest
from django.db.utils import IntegrityError

from berth_reservations.tests.conftest import *  # noqa

from ..models import CustomerProfile
from .factories import CustomerProfileFactory


def test_customer_profile_model(customer_profile):
    assert CustomerProfile.objects.count() == 1


def test_user_can_have_only_one_profile(customer_profile):
    with pytest.raises(IntegrityError):
        CustomerProfileFactory(user=customer_profile.user)
