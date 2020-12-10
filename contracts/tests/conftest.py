import base64

import pytest  # noqa

from berth_reservations.tests.conftest import *  # noqa
from contracts.services import VismaContractService
from contracts.tests.factories import BerthContractFactory, WinterStorageContractFactory
from payments.tests.conftest import order  # noqa

VISMA_SIGN_SERVICE_CONFIG = {
    "VISMASIGN_CLIENT_IDENTIFIER": "dummy-identifier",
    "VISMASIGN_SECRET": base64.b64encode("dummy-secret".encode("utf8")).decode("utf8"),
    "VISMASIGN_API_URL": "https://dummy-api-url",
    "VISMASIGN_TEST_SSN": "dummy-ssn",
}


@pytest.fixture
def visma_sign_service():
    return VismaContractService(config=VISMA_SIGN_SERVICE_CONFIG)


def _generate_visma_contract(contract_type):
    if contract_type == "winter_storage_contract":
        return WinterStorageContractFactory()
    elif contract_type == "berth_contract":
        return BerthContractFactory()


@pytest.fixture
def visma_contract(request):
    contract_type = request.param if hasattr(request, "param") else None
    return _generate_visma_contract(contract_type)
