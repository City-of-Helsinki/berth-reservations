import pytest

from berth_reservations.tests.utils import assert_in_errors
from payments.models import Order

from .utils import TestContractService

FULFILL_CONTRACT_MUTATION = """
  mutation FulfillContract($input: FulfillContractMutationInput!) {
    fulfillContract(input: $input) {
      signingUrl
    }
  }
"""

FULFILL_CONTRACT_MUTATION_INPUT = {
    "orderNumber": "1234",
    "returnUrl": "https://return-url.com",
    "authService": TestContractService.auth_methods[0]["identifier"],
}


@pytest.mark.parametrize(
    "order", ["berth_order", "winter_storage_order"], indirect=True
)
def test_fulfill_contract(superuser_api_client, order: Order):
    order.lease.contract.save()
    order.order_number = FULFILL_CONTRACT_MUTATION_INPUT["orderNumber"]
    order.save()
    executed = superuser_api_client.execute(
        FULFILL_CONTRACT_MUTATION, input=FULFILL_CONTRACT_MUTATION_INPUT
    )
    assert (
        executed["data"]["fulfillContract"]["signingUrl"]
        == TestContractService.signing_url
    )


def test_fulfill_contract_no_order(superuser_api_client):
    executed = superuser_api_client.execute(
        FULFILL_CONTRACT_MUTATION, input=FULFILL_CONTRACT_MUTATION_INPUT
    )
    assert_in_errors("No order found for given order number", executed)


@pytest.mark.parametrize(
    "order", ["berth_order", "winter_storage_order"], indirect=True
)
def test_fulfill_contract_no_contract_for_order(superuser_api_client, order: Order):
    order.lease.contract = None
    order.lease.save()
    order.order_number = FULFILL_CONTRACT_MUTATION_INPUT["orderNumber"]
    order.save()
    executed = superuser_api_client.execute(
        FULFILL_CONTRACT_MUTATION, input=FULFILL_CONTRACT_MUTATION_INPUT
    )
    assert_in_errors("No contract found for given order", executed)
