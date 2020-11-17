import abc
from typing import Dict, List

from leases.models import BerthLease, WinterStorageLease

from ..enums import ContractStatus
from ..models import BerthContract, Contract, WinterStorageContract


class ContractService(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def create_berth_contract(self, lease: BerthLease) -> BerthContract:
        """Create a new berth contract."""
        pass

    @abc.abstractmethod
    def create_winter_storage_contract(
        self, lease: WinterStorageLease
    ) -> WinterStorageContract:
        """Create a new winter storage contract."""
        pass

    @abc.abstractmethod
    def update_and_get_contract_status(self, contract: Contract) -> ContractStatus:
        """Get the contracts status."""
        pass

    @abc.abstractmethod
    def get_auth_methods(self) -> List[Dict]:
        """Get list of authentication methods."""
        pass

    @abc.abstractmethod
    def fulfill_contract(
        self, contract: Contract, auth_service: str, return_url: str
    ) -> str:
        """Gets the signing URL for the invitation."""
        pass

    @abc.abstractmethod
    def get_document(self, contract: Contract) -> bytes:
        """Get the contract document."""
        pass

    @staticmethod
    @abc.abstractmethod
    def get_config_template() -> Dict[str, type]:
        """Get the configuration template."""
        pass
