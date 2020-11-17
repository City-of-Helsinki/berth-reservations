import graphene
from django.core.exceptions import ObjectDoesNotExist

from payments.models import Order

from ..enums import ContractStatus
from ..services import get_contract_service
from .types import AuthMethod, ContractSignedType


class Query:
    contract_auth_methods = graphene.NonNull(
        graphene.List(graphene.NonNull(AuthMethod))
    )
    contract_signed = graphene.Field(
        ContractSignedType, order_number=graphene.NonNull(graphene.String)
    )

    def resolve_contract_auth_methods(self, info, **kwargs):
        return get_contract_service().get_auth_methods()

    def resolve_contract_signed(self, info, **kwargs):
        order_number = kwargs.get("order_number")

        try:
            order = Order.objects.get(order_number=order_number)
            contract = order.lease.contract
        except ObjectDoesNotExist:
            return ContractSignedType(is_signed=None)

        contract_status = get_contract_service().update_and_get_contract_status(
            contract
        )
        return ContractSignedType(is_signed=contract_status == ContractStatus.SIGNED)
