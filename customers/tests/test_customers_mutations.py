import random
import uuid

import pytest
from dateutil.utils import today
from django.core.files.uploadedfile import SimpleUploadedFile
from freezegun import freeze_time

from berth_reservations.tests.utils import (
    assert_doesnt_exist,
    assert_field_missing,
    assert_not_enough_permissions,
)
from customers.enums import BoatCertificateType
from customers.models import BoatCertificate, get_boat_media_folder
from customers.schema import BoatCertificateNode, BoatNode
from utils.relay import from_global_id, to_global_id

CREATE_BOAT_CERTIFICATE_MUTATION = """
mutation CREATE_CERTIFICATE($input: CreateBoatCertificateMutationInput!) {
    createBoatCertificate(input: $input) {
        boatCertificate {
            id
            boat {
                id
            }
            certificateType
            checkedAt
            checkedBy
            validUntil
            file
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_create_boat_certificate(api_client, boat):
    boat_id = to_global_id(BoatNode, boat.id)
    file_name = "certificate_file.pdf"
    check_date = today()

    variables = {
        "boatId": boat_id,
        "file": SimpleUploadedFile(
            name=file_name, content=None, content_type="application/pdf"
        ),
        "certificateType": random.choice(list(BoatCertificateType)).name,
        "validUntil": check_date,
        "checkedAt": check_date,
        "checkedBy": "John Wick",
    }

    assert BoatCertificate.objects.count() == 0

    executed = api_client.execute(CREATE_BOAT_CERTIFICATE_MUTATION, input=variables)

    # Assert the certificate was created
    assert BoatCertificate.objects.count() == 1
    certificate_id = executed["data"]["createBoatCertificate"]["boatCertificate"].pop(
        "id"
    )

    # Assert the returned id is not none
    assert certificate_id is not None

    # Assert that the returned file URL contains the right path
    assert get_boat_media_folder(
        BoatCertificate.objects.get(pk=from_global_id(certificate_id)), file_name
    ) in executed["data"]["createBoatCertificate"]["boatCertificate"].pop("file")

    # Assert the rest of the fields
    assert executed["data"]["createBoatCertificate"]["boatCertificate"] == {
        "boat": {"id": variables["boatId"]},
        "certificateType": variables["certificateType"],
        "validUntil": str(variables["validUntil"].date()),
        "checkedAt": str(variables["checkedAt"].date()),
        "checkedBy": variables["checkedBy"],
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbour_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_create_boat_certificate_not_enough_permissions(api_client, boat):
    variables = {
        "boatId": to_global_id(BoatNode, boat.id),
        "certificateType": random.choice(list(BoatCertificateType)).name,
    }
    assert BoatCertificate.objects.count() == 0

    executed = api_client.execute(CREATE_BOAT_CERTIFICATE_MUTATION, input=variables)

    assert BoatCertificate.objects.count() == 0
    assert_not_enough_permissions(executed)


def test_create_boat_certificate_no_boat(superuser_api_client):
    variables = {
        "certificateType": random.choice(list(BoatCertificateType)).name,
    }
    assert BoatCertificate.objects.count() == 0

    executed = superuser_api_client.execute(
        CREATE_BOAT_CERTIFICATE_MUTATION, input=variables
    )

    assert BoatCertificate.objects.count() == 0
    assert_field_missing("boat", executed)


def test_create_boat_certificate_boat_doesnt_exist(superuser_api_client):
    variables = {
        "boatId": to_global_id(BoatNode, uuid.uuid4()),
        "certificateType": random.choice(list(BoatCertificateType)).name,
    }
    assert BoatCertificate.objects.count() == 0

    executed = superuser_api_client.execute(
        CREATE_BOAT_CERTIFICATE_MUTATION, input=variables
    )

    assert BoatCertificate.objects.count() == 0
    assert_doesnt_exist("Boat", executed)


def test_create_boat_certificate_no_certificate_type(superuser_api_client, boat):
    variables = {
        "boatId": to_global_id(BoatNode, boat.id),
    }
    assert BoatCertificate.objects.count() == 0

    executed = superuser_api_client.execute(
        CREATE_BOAT_CERTIFICATE_MUTATION, input=variables
    )

    assert BoatCertificate.objects.count() == 0
    assert_field_missing("certificateType", executed)


UPDATE_BOAT_CERTIFICATE_MUTATION = """
mutation UPDATE_CERTIFICATE($input: UpdateBoatCertificateMutationInput!) {
    updateBoatCertificate(input: $input) {
        boatCertificate {
            id
            boat {
                id
            }
            certificateType
            checkedAt
            checkedBy
            validUntil
            file
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_update_boat_certificate(api_client, boat_certificate):
    certificate_id = to_global_id(BoatCertificateNode, boat_certificate.id)

    old_file_name = "old_certificate_file.pdf"
    new_file_name = "new_certificate_file.pdf"
    check_date = today()

    boat_certificate.file = SimpleUploadedFile(
        name=old_file_name, content=None, content_type="application/pdf"
    )
    boat_certificate.save()

    variables = {
        "id": certificate_id,
        "file": SimpleUploadedFile(
            name=new_file_name, content=None, content_type="application/pdf"
        ),
        "certificateType": random.choice(list(BoatCertificateType)).name,
        "validUntil": check_date,
        "checkedAt": check_date,
        "checkedBy": "John Wick",
    }

    assert BoatCertificate.objects.count() == 1

    executed = api_client.execute(UPDATE_BOAT_CERTIFICATE_MUTATION, input=variables)

    # Assert no more certificates were created
    assert BoatCertificate.objects.count() == 1

    # Assert that the returned file URL conatins the right path
    assert get_boat_media_folder(
        BoatCertificate.objects.get(pk=from_global_id(certificate_id)), new_file_name
    ) in executed["data"]["updateBoatCertificate"]["boatCertificate"].pop("file")

    # Assert the rest of the fields
    assert executed["data"]["updateBoatCertificate"]["boatCertificate"] == {
        "id": variables["id"],
        "boat": {"id": to_global_id(BoatNode, boat_certificate.boat.id)},
        "certificateType": variables["certificateType"],
        "validUntil": str(variables["validUntil"].date()),
        "checkedAt": str(variables["checkedAt"].date()),
        "checkedBy": variables["checkedBy"],
    }


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
@freeze_time("2020-01-01T08:00:00Z")
def test_update_boat_certificate_remove_fields(api_client, boat_certificate):
    certificate_id = to_global_id(BoatCertificateNode, boat_certificate.id)

    file_name = "old_certificate_file.pdf"

    boat_certificate.file = SimpleUploadedFile(
        name=file_name, content=None, content_type="application/pdf"
    )
    boat_certificate.save()

    variables = {
        "id": certificate_id,
        "file": None,
        "validUntil": None,
        "checkedBy": None,
    }

    assert BoatCertificate.objects.count() == 1

    executed = api_client.execute(UPDATE_BOAT_CERTIFICATE_MUTATION, input=variables)

    # Assert the certificate was created
    assert BoatCertificate.objects.count() == 1

    # Assert the rest of the fields
    assert executed["data"]["updateBoatCertificate"]["boatCertificate"] == {
        "id": variables["id"],
        "boat": {"id": to_global_id(BoatNode, boat_certificate.boat.id)},
        "certificateType": boat_certificate.certificate_type.name,
        "validUntil": None,
        "checkedAt": str(boat_certificate.checked_at),
        "checkedBy": None,
        "file": None,
    }


def test_update_boat_certificate_no_id(superuser_api_client):
    variables = {"file": None}
    assert BoatCertificate.objects.count() == 0

    executed = superuser_api_client.execute(
        UPDATE_BOAT_CERTIFICATE_MUTATION, input=variables
    )

    assert BoatCertificate.objects.count() == 0
    assert_field_missing("id", executed)


def test_update_boat_certificate_doesnt_exist(superuser_api_client):
    variables = {"id": to_global_id(BoatCertificateNode, uuid.uuid4())}
    assert BoatCertificate.objects.count() == 0

    executed = superuser_api_client.execute(
        UPDATE_BOAT_CERTIFICATE_MUTATION, input=variables
    )

    assert BoatCertificate.objects.count() == 0
    assert_doesnt_exist("BoatCertificate", executed)


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbour_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_update_boat_certificate_not_enough_permissions(api_client):
    variables = {"id": to_global_id(BoatCertificateNode, uuid.uuid4())}
    assert BoatCertificate.objects.count() == 0

    executed = api_client.execute(UPDATE_BOAT_CERTIFICATE_MUTATION, input=variables)

    assert BoatCertificate.objects.count() == 0
    assert_not_enough_permissions(executed)


DELETE_BOAT_CERTIFICATE_MUTATION = """
mutation DELETE_CERTIFICATE($input: DeleteBoatCertificateMutationInput!) {
    deleteBoatCertificate(input: $input) {
        __typename
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
def test_delete_boat_certificate(api_client, boat_certificate):
    variables = {"id": to_global_id(BoatCertificateNode, boat_certificate.id)}

    assert BoatCertificate.objects.count() == 1

    api_client.execute(DELETE_BOAT_CERTIFICATE_MUTATION, input=variables)

    assert BoatCertificate.objects.count() == 0


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "harbour_services", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_delete_boat_certificate_not_enough_permissions(api_client, boat_certificate):
    variables = {"id": to_global_id(BoatCertificateNode, boat_certificate.id)}

    assert BoatCertificate.objects.count() == 1

    executed = api_client.execute(DELETE_BOAT_CERTIFICATE_MUTATION, input=variables)

    assert BoatCertificate.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_delete_boat_certificate_doesnt_exist(superuser_api_client, boat_certificate):
    variables = {"id": to_global_id(BoatCertificateNode, uuid.uuid4())}
    assert BoatCertificate.objects.count() == 1

    executed = superuser_api_client.execute(
        UPDATE_BOAT_CERTIFICATE_MUTATION, input=variables
    )

    assert BoatCertificate.objects.count() == 1
    assert_doesnt_exist("BoatCertificate", executed)
