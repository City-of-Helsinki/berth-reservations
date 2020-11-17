import pytest

from payments.models import Order

from ..enums import ContractStatus
from .utils import TestContractService

CONTRACT_SIGNED_QUERY = """
{
  contractSigned(orderNumber: "%s") {
    isSigned
  }
}
"""


@pytest.mark.parametrize(
    "order", ["berth_order", "winter_storage_order"], indirect=True
)
@pytest.mark.parametrize("new_status", ContractStatus.values)
def test_contract_signed(old_schema_api_client, order: Order, new_status):
    order.lease.contract.status = ContractStatus(new_status)
    order.lease.contract.save()
    executed = old_schema_api_client.execute(CONTRACT_SIGNED_QUERY % order.order_number)
    assert executed == {
        "data": {
            "contractSigned": {
                "isSigned": TestContractService.new_contract_status
                == ContractStatus.SIGNED
            }
        }
    }


def test_contract_signed_non_existent_order(old_schema_api_client):
    query = CONTRACT_SIGNED_QUERY % "order_that_doesnt_exist"
    executed = old_schema_api_client.execute(query)
    assert executed == {"data": {"contractSigned": {"isSigned": None}}}


@pytest.mark.parametrize(
    "order", ["berth_order", "winter_storage_order"], indirect=True
)
def test_contract_signed_lease_with_no_contract(old_schema_api_client, order: Order):
    order.lease.contract = None
    order.lease.save()
    executed = old_schema_api_client.execute(CONTRACT_SIGNED_QUERY % order.order_number)
    assert executed == {"data": {"contractSigned": {"isSigned": None}}}


CONTRACT_AUTH_METHODS_QUERY = """
    {
      contractAuthMethods {
        identifier
        name
        image
      }
    }
"""


def test_contract_auth_methods(old_schema_api_client):
    executed = old_schema_api_client.execute(CONTRACT_AUTH_METHODS_QUERY)
    assert executed == {
        "data": {"contractAuthMethods": TestContractService.auth_methods}
    }
