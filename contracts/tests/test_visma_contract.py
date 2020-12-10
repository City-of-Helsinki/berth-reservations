import uuid
from unittest import mock

import pytest

from leases.tests.factories import BerthLeaseFactory, WinterStorageLeaseFactory

from ..enums import ContractStatus
from ..models import Contract
from .utils import (
    mocked_visma_create_contract_requests,
    mocked_visma_fulfill_contract_request,
    mocked_visma_get_auth_methods_request,
    mocked_visma_get_document_request,
    mocked_visma_get_status_request,
)


def test_create_berth_contract(visma_sign_service):
    document_id = str(uuid.uuid4())
    invitation_id = str(uuid.uuid4())
    passphrase = "test-passphrase"
    lease = BerthLeaseFactory()

    with mock.patch(
        "requests.request",
        side_effect=mocked_visma_create_contract_requests(
            document_id, invitation_id, passphrase
        ),
    ):
        contract = visma_sign_service.create_berth_contract(lease)

    assert contract.document_id == document_id
    assert contract.invitation_id == invitation_id
    assert contract.passphrase == passphrase
    assert contract.lease == lease


def test_create_winter_storage_contract(visma_sign_service):
    document_id = str(uuid.uuid4())
    invitation_id = str(uuid.uuid4())
    passphrase = "test-passphrase"
    lease = WinterStorageLeaseFactory()

    with mock.patch(
        "requests.request",
        side_effect=mocked_visma_create_contract_requests(
            document_id, invitation_id, passphrase
        ),
    ):
        contract = visma_sign_service.create_winter_storage_contract(lease)

    assert contract.document_id == document_id
    assert contract.invitation_id == invitation_id
    assert contract.passphrase == passphrase
    assert contract.lease == lease


@pytest.mark.parametrize(
    "visma_contract", ["berth_contract", "winter_storage_contract"], indirect=True
)
@pytest.mark.parametrize("new_status", ContractStatus.values)
def test_update_and_get_contract_status(
    visma_sign_service, visma_contract: Contract, new_status: ContractStatus
):
    with mock.patch(
        "requests.request", side_effect=mocked_visma_get_status_request(new_status)
    ):
        returned_status = visma_sign_service.update_and_get_contract_status(
            visma_contract
        )
    assert returned_status == ContractStatus(new_status)
    assert visma_contract.status == ContractStatus(new_status)


def test_get_auth_methods(visma_sign_service):
    auth_methods = [
        {
            "identifier": "tupas-tbank",
            "name": "Fraktio Oy",
            "image": "https://vismasign.frakt.io/img/test-identification.png",
        }
    ]
    with mock.patch(
        "requests.request",
        side_effect=mocked_visma_get_auth_methods_request(auth_methods),
    ):
        returned_auth_methods = visma_sign_service.get_auth_methods()
    assert returned_auth_methods == auth_methods


@pytest.mark.parametrize(
    "visma_contract", ["berth_contract", "winter_storage_contract"], indirect=True
)
def test_fulfill_contract(visma_sign_service, visma_contract):
    signing_url = "https://signing-url"
    with mock.patch(
        "requests.request",
        side_effect=mocked_visma_fulfill_contract_request(signing_url),
    ):
        returned_signing_url = visma_sign_service.fulfill_contract(
            visma_contract, "", ""
        )
    assert returned_signing_url == signing_url


@pytest.mark.parametrize(
    "visma_contract", ["berth_contract", "winter_storage_contract"], indirect=True
)
def test_get_document(visma_sign_service, visma_contract):
    document_data = b""
    with mock.patch(
        "requests.request", side_effect=mocked_visma_get_document_request(document_data)
    ):
        returned_document = visma_sign_service.get_document(visma_contract)

    assert returned_document == document_data
