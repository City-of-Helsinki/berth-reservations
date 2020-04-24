import os
import random
from pathlib import Path

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.utils import IntegrityError

from berth_reservations.tests.conftest import *  # noqa
from berth_reservations.tests.factories import CustomerProfileFactory

from ..enums import BoatCertificateType, OrganizationType
from ..models import BoatCertificate, CustomerProfile, Organization
from .factories import BoatCertificateFactory, OrganizationFactory


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


def test_boat_certificate_cannot_change_boat(boat_certificate, boat):
    with pytest.raises(ValidationError) as exception:
        boat_certificate.boat = boat
        boat_certificate.save()

    assert "Cannot change the boat assigned to this certificate" in str(exception.value)


def test_boat_certificate_can_only_have_one_per_type(boat):
    BoatCertificateFactory(boat=boat, certificate_type=BoatCertificateType.INSPECTION)
    with pytest.raises(ValidationError) as exception:
        BoatCertificateFactory(
            boat=boat, certificate_type=BoatCertificateType.INSPECTION
        )

    assert "Boat certificate with this Boat and Certificate type already exists" in str(
        exception.value
    )

    BoatCertificateFactory(boat=boat, certificate_type=BoatCertificateType.INSURANCE)
    with pytest.raises(ValidationError) as exception:
        BoatCertificateFactory(
            boat=boat, certificate_type=BoatCertificateType.INSURANCE
        )

    assert "Boat certificate with this Boat and Certificate type already exists" in str(
        exception.value
    )
    assert BoatCertificate.objects.filter(boat=boat).count() == 2


def test_boat_certificate_file_removed(boat):
    file_name = "certficate.pdf"
    certificate = BoatCertificate.objects.create(
        boat=boat,
        certificate_type=random.choice(list(BoatCertificateType)),
        file=SimpleUploadedFile(
            name=file_name, content=None, content_type="application/pdf"
        ),
    )

    directory = Path(certificate.file.path).parent
    files = os.listdir(directory)

    # Test that the directory contains the image
    assert len(files) == 1
    assert files[0] == file_name

    certificate.file = None
    certificate.save()

    # Test that the image is being removed from the directory
    files = os.listdir(directory)
    assert len(files) == 0


def test_boat_certificate_file_replaced(boat):
    file_name_1 = "certificate1.pdf"
    file_name_2 = "certificate2.pdf"

    certificate = BoatCertificate.objects.create(
        boat=boat,
        certificate_type=random.choice(list(BoatCertificateType)),
        file=SimpleUploadedFile(
            name=file_name_1, content=None, content_type="application/pdf"
        ),
    )

    directory = Path(certificate.file.path).parent
    files = os.listdir(directory)

    # Test that the directory contains the image
    assert len(files) == 1
    assert files[0] == file_name_1

    certificate.file = SimpleUploadedFile(
        name=file_name_2, content=None, content_type="application/pdf"
    )
    certificate.save()

    files = os.listdir(directory)
    # Test that the image is being removed from the directory
    assert len(files) == 1
    assert files[0] == file_name_2
