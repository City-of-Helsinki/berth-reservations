import os
import random
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.utils import IntegrityError

from berth_reservations.tests.conftest import *  # noqa
from berth_reservations.tests.factories import CustomerProfileFactory
from leases.enums import LeaseStatus
from resources.tests.factories import BerthFactory, BoatTypeFactory, PierFactory

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


def test_import_customer_data_with_valid_data_set():
    berth1 = BerthFactory()
    berth2 = BerthFactory()
    berth3 = BerthFactory()
    boat_type1 = BoatTypeFactory()
    boat_type2 = BoatTypeFactory()
    data = [
        {
            "customer_id": "313431",
            "leases": [
                {
                    "harbor_servicemap_id": berth1.pier.harbor.servicemap_id,
                    "berth_number": berth1.number,
                    "pier_id": berth1.pier.identifier,
                    "start_date": "2019-06-10",
                    "end_date": "2019-09-14",
                    "boat_index": 0,
                }
            ],
            "boats": [
                {
                    "boat_type": boat_type1.name,
                    "name": "McBoatface 111",
                    "registration_number": "31123A",
                    "width": "2.00",
                    "length": "5.30",
                    "draught": None,
                    "weight": None,
                }
            ],
            "orders": [
                {
                    "created_at": "2019-12-02 00:00:00.000",
                    "order_sum": "251.00",
                    "vat_percentage": "25.0",
                    "is_paid": True,
                    "berth": {
                        "harbor_servicemap_id": berth2.pier.harbor.servicemap_id,
                        "pier_id": berth2.pier.identifier,
                        "berth_number": berth2.number,
                    },
                    "comment": "Laskunumero: 247509 RAMSAYRANTA A 004",
                }
            ],
            "organization": {
                "type": "company",
                "name": "Nice Profitable Firm Ltd.",
                "address": "Mannerheimintie 1 A 1",
                "postal_code": "00100",
                "city": "Helsinki",
            },
            "comment": "VENEPAIKKA PERUTTU 9.1.2012 Hetu/Y-tunnus Timmistä: 01018000T",
            "id": "98edea83-4c92-4dda-bb90-f22e9dafe94c",
        },
        {
            "customer_id": "313432",
            "leases": [
                {
                    "harbor_servicemap_id": berth3.pier.harbor.servicemap_id,
                    "pier_id": berth3.pier.identifier,
                    "berth_number": berth3.number,
                    "start_date": "2019-06-10",
                    "end_date": "2019-09-14",
                }
            ],
            "boats": [
                {
                    "boat_type": boat_type2.name,
                    "name": "My Boaty",
                    "registration_number": "",
                    "width": "1.40",
                    "length": "3.30",
                    "draught": None,
                    "weight": 500,
                }
            ],
            "orders": [],
            "comment": "",
            "id": "48319ebc-5eaf-4285-a565-15848225614b",
        },
    ]

    assert CustomerProfile.objects.count() == 0

    result = CustomerProfile.objects.import_customer_data(data)

    # Test both customers were created
    assert CustomerProfile.objects.count() == 2
    assert len(result.keys()) == 2

    # First customer
    customer1 = CustomerProfile.objects.get(id=data[0].get("id"))

    assert customer1.organization.name == data[0].get("organization", {}).get("name")
    assert customer1.orders.count() == 1
    assert customer1.boats.count() == 1
    assert customer1.berth_leases.count() == 2

    assert customer1.boats.first().registration_number == "31123A"

    # Test that the lease belongs to the berth specified
    assert (
        customer1.berth_leases.filter(
            berth__number=berth1.number, berth__pier__harbor=berth1.pier.harbor
        ).count()
        == 1
    )
    order = customer1.orders.first()
    assert order.lease.berth.number == berth2.number
    assert order.lease.status == LeaseStatus.PAID
    assert order.price == Decimal("251.00")
    assert order.tax_percentage == Decimal("25.00")
    assert order.order_lines.count() == 0

    # First customer
    customer2 = CustomerProfile.objects.get(id=data[1].get("id"))

    assert not hasattr(customer2, "organization")
    assert customer2.orders.count() == 0
    assert customer2.boats.count() == 1

    # Test that the lease belongs to the berth specified
    assert (
        customer2.berth_leases.filter(
            berth__number=berth3.number, berth__pier__harbor=berth3.pier.harbor
        ).count()
        == 1
    )


def test_import_customer_data_missing_id():
    data = [
        {
            "customer_id": "313431",
            "leases": [],
            "boats": [],
            "orders": [],
            "comment": "VENEPAIKKA PERUTTU 9.1.2012 Hetu/Y-tunnus Timmistä: 01018000T",
        },
    ]

    assert CustomerProfile.objects.count() == 0
    with pytest.raises(Exception) as e:
        CustomerProfile.objects.import_customer_data(data)

    assert "No customer ID provided" in str(e)
    assert CustomerProfile.objects.count() == 0


def test_import_customer_data_lease_many_piers_no_berth_found(berth, boat_type):
    BerthFactory(pier=PierFactory(harbor=berth.pier.harbor), number=berth.number)

    data = [
        {
            "customer_id": "313432",
            "leases": [
                {
                    "harbor_servicemap_id": berth.pier.harbor.servicemap_id,
                    "pier_id": "Fake-identifier",
                    "berth_number": berth.number,
                    "start_date": "2019-06-10",
                    "end_date": "2019-09-14",
                    "boat_index": 0,
                }
            ],
            "boats": [
                {
                    "boat_type": boat_type.name,
                    "name": "My Boaty",
                    "registration_number": "",
                    "width": "1.40",
                    "length": "3.30",
                    "draught": None,
                    "weight": 500,
                }
            ],
            "orders": [],
            "comment": "",
            "id": "48319ebc-5eaf-4285-a565-15848225614b",
        }
    ]

    assert CustomerProfile.objects.count() == 0
    with pytest.raises(Exception) as e:
        CustomerProfile.objects.import_customer_data(data)

    assert f"Berth {berth.number} does not exist on pier Fake-identifier" in str(e)
    assert CustomerProfile.objects.count() == 0


def test_import_customer_data_lease_many_piers_default_berth(berth, boat_type):
    data = [
        {
            "customer_id": "313432",
            "leases": [
                {
                    "harbor_servicemap_id": berth.pier.harbor.servicemap_id,
                    "pier_id": "Fake-identifier",
                    "berth_number": berth.number,
                    "start_date": "2019-06-10",
                    "end_date": "2019-09-14",
                    "boat_index": 0,
                }
            ],
            "boats": [
                {
                    "boat_type": boat_type.name,
                    "name": "My Boaty",
                    "registration_number": "",
                    "width": "1.40",
                    "length": "3.30",
                    "draught": None,
                    "weight": 500,
                }
            ],
            "orders": [],
            "comment": "",
            "id": "48319ebc-5eaf-4285-a565-15848225614b",
        }
    ]

    assert CustomerProfile.objects.count() == 0

    result = CustomerProfile.objects.import_customer_data(data)

    assert CustomerProfile.objects.count() == 1

    assert result == {"313432": UUID("48319ebc-5eaf-4285-a565-15848225614b")}
    profile = CustomerProfile.objects.first()
    assert profile.berth_leases.first().berth.pier.identifier != "Fake-identifier"
    assert profile.berth_leases.first().berth.number == berth.number


def test_import_customer_data_order_many_piers_no_berth_found(berth, boat_type):
    BerthFactory(pier=PierFactory(harbor=berth.pier.harbor), number=berth.number)

    data = [
        {
            "customer_id": "313432",
            "leases": [],
            "boats": [],
            "orders": [
                {
                    "created_at": "2019-12-02 00:00:00.000",
                    "order_sum": "251.00",
                    "vat_percentage": "25.0",
                    "is_paid": True,
                    "berth": {
                        "harbor_servicemap_id": berth.pier.harbor.servicemap_id,
                        "pier_id": "Fake-identifier",
                        "berth_number": berth.number,
                    },
                    "comment": "Laskunumero: 247509 RAMSAYRANTA A 004",
                }
            ],
            "comment": "",
            "id": "48319ebc-5eaf-4285-a565-15848225614b",
        }
    ]

    assert CustomerProfile.objects.count() == 0
    with pytest.raises(Exception) as e:
        CustomerProfile.objects.import_customer_data(data)

    assert f"Berth {berth.number} does not exist on pier Fake-identifier" in str(e)
    assert CustomerProfile.objects.count() == 0


def test_import_customer_data_order_many_piers_default_berth(berth, boat_type):
    data = [
        {
            "customer_id": "313432",
            "leases": [],
            "boats": [],
            "orders": [
                {
                    "created_at": "2019-12-02 00:00:00.000",
                    "order_sum": "251.00",
                    "vat_percentage": "25.0",
                    "is_paid": True,
                    "berth": {
                        "harbor_servicemap_id": berth.pier.harbor.servicemap_id,
                        "pier_id": "Fake-identifier",
                        "berth_number": berth.number,
                    },
                    "comment": "Laskunumero: 247509 RAMSAYRANTA A 004",
                }
            ],
            "comment": "",
            "id": "48319ebc-5eaf-4285-a565-15848225614b",
        }
    ]

    assert CustomerProfile.objects.count() == 0

    result = CustomerProfile.objects.import_customer_data(data)

    assert CustomerProfile.objects.count() == 1

    assert result == {"313432": UUID("48319ebc-5eaf-4285-a565-15848225614b")}
    profile = CustomerProfile.objects.first()

    assert profile.orders.count() == 1
    assert profile.berth_leases.count() == 1

    lease = profile.berth_leases.first()

    assert profile.orders.first().lease == lease

    assert lease.berth.pier.identifier != "Fake-identifier"
    assert lease.berth.number == berth.number
