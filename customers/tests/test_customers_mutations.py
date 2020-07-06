import random
import uuid

import pytest
from dateutil.utils import today
from django.core.files.uploadedfile import SimpleUploadedFile

from berth_reservations.tests.utils import (
    assert_doesnt_exist,
    assert_field_missing,
    assert_not_enough_permissions,
)
from customers.enums import BoatCertificateType
from customers.models import (
    Boat,
    BoatCertificate,
    get_boat_certificate_media_folder,
    get_boat_media_folder,
)
from customers.schema import BoatCertificateNode, BoatNode, ProfileNode
from customers.tests.factories import BoatCertificateFactory
from resources.schema import BoatTypeType
from utils.numbers import random_decimal
from utils.relay import from_global_id, to_global_id

CREATE_BOAT_MUTATION = """
mutation CREATE_BOAT($input: CreateBoatMutationInput!) {
    createBoat(input: $input) {
        boat {
            owner {
                id
            }
            boatType {
                id
            }
            name
            length
            width
            certificates {
                id
                certificateType
                checkedAt
                checkedBy
                validUntil
                file
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
def test_create_boat(api_client, customer_profile, boat_type):
    check_date = today().date()
    file_name = "certificate.pdf"
    owner_id = to_global_id(ProfileNode, customer_profile.id)
    boat_type_id = str(boat_type.id)

    variables = {
        "ownerId": owner_id,
        "boatTypeId": boat_type_id,
        "name": "Flying Dutchman",
        "length": random_decimal(as_string=True),
        "width": random_decimal(as_string=True),
        "addBoatCertificates": [
            {
                "file": SimpleUploadedFile(
                    name=file_name, content=None, content_type="application/pdf"
                ),
                "certificateType": random.choice(list(BoatCertificateType)).name,
                "validUntil": str(check_date),
                "checkedAt": str(check_date),
                "checkedBy": "John Wick",
            }
        ],
    }

    assert Boat.objects.count() == 0
    assert BoatCertificate.objects.count() == 0

    executed = api_client.execute(CREATE_BOAT_MUTATION, input=variables)

    certificates = executed["data"]["createBoat"]["boat"].pop("certificates")

    assert Boat.objects.count() == 1
    assert BoatCertificate.objects.count() == 1

    assert len(certificates) == 1

    # Test that all the expected files are in the instance certificates
    cert = certificates[0]
    cert_id = cert.pop("id")

    assert cert_id is not None
    cert_id = from_global_id(cert_id, BoatCertificateNode)

    assert get_boat_certificate_media_folder(
        BoatCertificate.objects.get(id=cert_id), "certificate.pdf"
    ) in cert.pop("file")
    assert cert == {
        "certificateType": variables["addBoatCertificates"][0]["certificateType"],
        "validUntil": str(check_date),
        "checkedAt": str(check_date),
        "checkedBy": "John Wick",
    }

    assert executed["data"]["createBoat"]["boat"] == {
        "owner": {"id": owner_id},
        "boatType": {"id": boat_type_id},
        "name": variables["name"],
        "length": variables["length"],
        "width": variables["width"],
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbour_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_create_boat_not_enough_permissions(api_client, customer_profile, boat_type):
    owner_id = to_global_id(ProfileNode, customer_profile.id)
    boat_type_id = str(boat_type.id)

    variables = {
        "ownerId": owner_id,
        "boatTypeId": boat_type_id,
        "length": random_decimal(),
        "width": random_decimal(),
    }

    assert Boat.objects.count() == 0

    executed = api_client.execute(CREATE_BOAT_MUTATION, input=variables)

    assert Boat.objects.count() == 0
    assert_not_enough_permissions(executed)


def test_create_boat_no_owner(superuser_api_client):
    variables = {
        "boatTypeId": to_global_id(BoatTypeType, uuid.uuid4()),
    }
    assert Boat.objects.count() == 0

    executed = superuser_api_client.execute(CREATE_BOAT_MUTATION, input=variables)

    assert Boat.objects.count() == 0
    assert_field_missing("owner", executed)


def test_create_boat_no_boat_type(superuser_api_client):
    variables = {
        "ownerId": to_global_id(ProfileNode, uuid.uuid4()),
    }
    assert Boat.objects.count() == 0

    executed = superuser_api_client.execute(CREATE_BOAT_MUTATION, input=variables)

    assert Boat.objects.count() == 0
    assert_field_missing("boatType", executed)


UPDATE_BOAT_MUTATION = """
mutation UPDATE_BOAT($input: UpdateBoatMutationInput!) {
    updateBoat(input: $input) {
        boat {
            owner {
                id
            }
            boatType {
                id
            }
            name
            length
            width
            certificates {
                id
                certificateType
                file
                checkedBy
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
def test_update_boat(api_client, boat):
    boat_id = to_global_id(BoatNode, boat.id)
    owner_id = to_global_id(ProfileNode, boat.owner.id)
    boat_type_id = str(boat.boat_type.id)

    file_name_keep = "certificate-keep.pdf"
    file_name_delete = "certificate-delete.pdf"
    certificate_delete = BoatCertificateFactory(
        boat=boat, file=SimpleUploadedFile(name=file_name_delete, content=None)
    )

    variables = {
        "id": boat_id,
        "name": "Flying Dutchman",
        "length": random_decimal(as_string=True),
        "width": random_decimal(as_string=True),
        "addBoatCertificates": [
            {
                "file": SimpleUploadedFile(
                    name=file_name_keep, content=None, content_type="application/pdf"
                ),
                "certificateType": random.choice(list(BoatCertificateType)).name,
                "checkedBy": "John Wick",
            }
        ],
        "removeBoatCertificates": [
            to_global_id(BoatCertificateNode, certificate_delete.id)
        ],
    }

    assert Boat.objects.count() == 1
    assert BoatCertificate.objects.count() == 1

    executed = api_client.execute(UPDATE_BOAT_MUTATION, input=variables)

    certificates = executed["data"]["updateBoat"]["boat"].pop("certificates")

    assert Boat.objects.count() == 1
    assert BoatCertificate.objects.count() == 1

    assert len(certificates) == 1

    # Test that all the expected files are in the instance certificates
    cert = certificates[0]
    cert_id = cert.pop("id")

    assert cert_id is not None
    cert_id = from_global_id(cert_id)

    # Check that the old file was removed
    assert get_boat_certificate_media_folder(
        BoatCertificate.objects.get(id=cert_id), file_name_delete
    ) not in cert.get("file")

    # Check that the new file has a valid url
    assert get_boat_certificate_media_folder(
        BoatCertificate.objects.get(id=cert_id), file_name_keep
    ) in cert.pop("file")

    assert cert == {
        "certificateType": variables["addBoatCertificates"][0]["certificateType"],
        "checkedBy": variables["addBoatCertificates"][0]["checkedBy"],
    }

    assert executed["data"]["updateBoat"]["boat"] == {
        "owner": {"id": owner_id},
        "boatType": {"id": boat_type_id},
        "name": variables["name"],
        "length": variables["length"],
        "width": variables["width"],
    }


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
def test_update_boat_certificates(api_client, boat):
    boat_id = to_global_id(BoatNode, boat.id)

    file_name_1 = "certificate-1.pdf"
    file_name_2 = "certificate-2.pdf"
    new_checked_by = "John Wick"

    certificate_1 = BoatCertificateFactory(
        boat=boat,
        file=SimpleUploadedFile(name="old-filename-1.pdf", content=None),
        certificate_type=BoatCertificateType.INSURANCE,
        checked_by="Old checked by",
    )
    certificate_1_id = to_global_id(BoatCertificateNode, certificate_1.id)
    certificate_2 = BoatCertificateFactory(
        boat=boat,
        file=SimpleUploadedFile(name="old-filename-2.pdf", content=None),
        certificate_type=BoatCertificateType.INSPECTION,
        checked_by="Old checked by",
    )
    certificate_2_id = to_global_id(BoatCertificateNode, certificate_2.id)

    variables = {
        "id": boat_id,
        "updateBoatCertificates": [
            {
                "id": certificate_1_id,
                "file": SimpleUploadedFile(name=file_name_1, content=None),
                "checkedBy": new_checked_by,
            },
            {
                "id": certificate_2_id,
                "file": SimpleUploadedFile(name=file_name_2, content=None),
                "checkedBy": new_checked_by,
            },
        ],
    }

    assert BoatCertificate.objects.count() == 2

    executed = api_client.execute(UPDATE_BOAT_MUTATION, input=variables)

    certificates = executed["data"]["updateBoat"]["boat"].get("certificates")

    assert BoatCertificate.objects.count() == 2

    assert len(certificates) == 2

    # Test that all the expected files are in the instance certificates
    expected_urls = [
        get_boat_media_folder(boat, file_name_1),
        get_boat_media_folder(boat, file_name_2),
    ]

    for cert in certificates:
        assert any([expected_url in cert.get("file") for expected_url in expected_urls])
        assert cert.get("checkedBy") == new_checked_by


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbour_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_update_boat_not_enough_permissions(api_client, boat):
    variables = {"id": to_global_id(BoatNode, boat.id)}
    assert Boat.objects.count() == 1

    executed = api_client.execute(UPDATE_BOAT_MUTATION, input=variables)

    assert Boat.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_update_boat_no_id(superuser_api_client, boat):
    variables = {"name": "foobar"}
    assert Boat.objects.count() == 1

    executed = superuser_api_client.execute(UPDATE_BOAT_MUTATION, input=variables)

    assert Boat.objects.count() == 1
    assert_field_missing("id", executed)


DELETE_BOAT_MUTATION = """
mutation DELETE_BOAT($input: DeleteBoatMutationInput!) {
    deleteBoat(input: $input) {
        __typename
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
def test_delete_boat(api_client, boat):
    variables = {
        "id": to_global_id(BoatNode, boat.id),
    }

    assert Boat.objects.count() == 1

    api_client.execute(DELETE_BOAT_MUTATION, input=variables)

    assert Boat.objects.count() == 0


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbour_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_delete_not_enough_permissions(api_client, boat):
    variables = {"id": to_global_id(BoatNode, boat.id)}
    assert Boat.objects.count() == 1

    executed = api_client.execute(DELETE_BOAT_MUTATION, input=variables)

    assert Boat.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_delete_berth_inexistent_boat(superuser_api_client):
    variables = {
        "id": to_global_id(BoatNode, uuid.uuid4()),
    }

    executed = superuser_api_client.execute(DELETE_BOAT_MUTATION, input=variables)

    assert_doesnt_exist("Boat", executed)
