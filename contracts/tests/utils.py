from typing import Dict, List

from leases.models import BerthLease, WinterStorageLease

from ..enums import ContractStatus
from ..models import BerthContract, Contract, WinterStorageContract
from ..services.base import ContractService
from .factories import BerthContractFactory, WinterStorageContractFactory


class TestContractService(ContractService):
    auth_methods = [
        {"identifier": "test-auth-method", "name": "Test Method", "image": "image"}
    ]
    signing_url = "https://dummy-signing-url"
    test_document_contents = b"test document contents"
    new_contract_status = ContractStatus.SIGNED

    def create_berth_contract(self, lease: BerthLease) -> BerthContract:
        lease.contract = BerthContractFactory(lease=lease)
        lease.contract.save()
        return lease.contract

    def create_winter_storage_contract(
        self, lease: WinterStorageLease
    ) -> WinterStorageContract:
        lease.contract = WinterStorageContractFactory(lease=lease)
        lease.contract.save()
        return lease.contract

    def update_and_get_contract_status(self, contract: Contract) -> ContractStatus:
        contract.status = self.new_contract_status
        contract.save()
        return ContractStatus(contract.status)

    def get_auth_methods(self) -> List[Dict]:
        return self.auth_methods

    def fulfill_contract(
        self, contract: Contract, auth_service: str, return_url: str
    ) -> str:
        return self.signing_url

    def get_document(self, contract: Contract) -> bytes:
        return self.test_document_contents

    @staticmethod
    def get_config_template() -> Dict[str, type]:
        return {}


class MockVismaResponse:
    def __init__(self, json=None, headers=None, content=None):
        self._json = json
        self.headers = headers
        self.content = content

    def json(self):
        return self._json

    def raise_for_status(self):
        pass


def mocked_visma_create_contract_requests(document_id, invitation_id, passphrase):
    def _mock_fn(*args, **kwargs):
        def _visma_url_match(api_url):
            return kwargs["url"].endswith(api_url)

        if _visma_url_match("/api/v1/document/"):
            return MockVismaResponse(headers={"Location": f"https://url/{document_id}"})

        if _visma_url_match(f"/api/v1/document/{document_id}/files"):
            return MockVismaResponse()

        if _visma_url_match(f"/api/v1/document/{document_id}/invitations"):
            return MockVismaResponse(
                json=[{"uuid": invitation_id, "passphrase": passphrase}]
            )

    return _mock_fn


def mocked_visma_get_status_request(new_status):
    def _mock_fn(*args, **kwargs):
        return MockVismaResponse(json={"status": new_status})

    return _mock_fn


def mocked_visma_get_auth_methods_request(auth_methods):
    def _mock_fn(*args, **kwargs):
        return MockVismaResponse(json={"methods": auth_methods})

    return _mock_fn


def mocked_visma_fulfill_contract_request(signing_url):
    def _mock_fn(*args, **kwargs):
        return MockVismaResponse(headers={"Location": signing_url})

    return _mock_fn


def mocked_visma_get_document_request(document_data):
    def _mock_fn(*args, **kwargs):
        return MockVismaResponse(content=document_data)

    return _mock_fn
