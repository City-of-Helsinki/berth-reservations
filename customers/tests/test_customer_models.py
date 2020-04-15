import pytest
from django.db.utils import IntegrityError

from berth_reservations.tests.conftest import *  # noqa
from berth_reservations.tests.factories import CustomerProfileFactory

from ..models import CustomerProfile, Organization
from .factories import OrganizationFactory


def test_customer_profile_model(customer_profile):
    assert CustomerProfile.objects.count() == 1


def test_user_can_have_only_one_profile(customer_profile):
    with pytest.raises(IntegrityError):
        CustomerProfileFactory(user=customer_profile.user)


def test_customer_can_have_organization_info(customer_profile):
    assert Organization.objects.count() == 0
    OrganizationFactory(customer=customer_profile)
    assert Organization.objects.count() == 1


def test_customer_can_have_only_one_organization():
    organization = OrganizationFactory()
    with pytest.raises(IntegrityError):
        OrganizationFactory(customer=organization.customer)
