import pytest
from django.db.utils import IntegrityError

from berth_reservations.tests.conftest import *  # noqa
from berth_reservations.tests.factories import CustomerProfileFactory

from ..models import Company, CustomerProfile
from .factories import CompanyFactory


def test_customer_profile_model(customer_profile):
    assert CustomerProfile.objects.count() == 1


def test_user_can_have_only_one_profile(customer_profile):
    with pytest.raises(IntegrityError):
        CustomerProfileFactory(user=customer_profile.user)


def test_customer_can_have_company_info(customer_profile):
    assert Company.objects.count() == 0
    CompanyFactory(customer=customer_profile)
    assert Company.objects.count() == 1


def test_customer_can_have_only_one_company():
    company = CompanyFactory()
    with pytest.raises(IntegrityError):
        CompanyFactory(customer=company.customer)
