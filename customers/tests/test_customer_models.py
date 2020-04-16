import pytest
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from berth_reservations.tests.conftest import *  # noqa
from berth_reservations.tests.factories import CustomerProfileFactory

from ..enums import OrganizationType
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
    with pytest.raises(ValidationError) as exception:
        OrganizationFactory(customer=organization.customer)

    assert "Organization with this Customer already exists" in str(exception.value)


def test_company_requires_business_id():
    with pytest.raises(ValidationError) as exception:
        OrganizationFactory(
            organization_type=OrganizationType.COMPANY, business_id="",
        )

    assert "A company must have a business id" in str(exception.value)
