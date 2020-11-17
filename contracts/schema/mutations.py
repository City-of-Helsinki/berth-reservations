import graphene
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.translation import gettext_lazy as _

from berth_reservations.exceptions import VenepaikkaGraphQLError
from payments.models import Order

from ..services import get_contract_service


class FulfillContractMutation(graphene.ClientIDMutation):
    class Input:
        order_number = graphene.NonNull(graphene.String)
        return_url = graphene.NonNull(graphene.String)
        auth_service = graphene.NonNull(graphene.String)

    signing_url = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        try:
            order = Order.objects.get(order_number=input.get("order_number"))
        except Order.DoesNotExist:
            raise VenepaikkaGraphQLError(_("No order found for given order number"))

        try:
            contract = order.lease.contract
        except Exception:
            raise VenepaikkaGraphQLError(_("No contract found for given order"))

        try:
            URLValidator()(input.get("return_url"))
        except ValidationError:
            raise VenepaikkaGraphQLError(_("return_url is not a valid URL"))

        auth_method_identifiers = map(
            lambda auth_method: auth_method["identifier"],
            get_contract_service().get_auth_methods(),
        )
        if input.get("auth_service") not in auth_method_identifiers:
            raise VenepaikkaGraphQLError(
                _("auth_service is not a supported authentication service")
            )

        signing_url = get_contract_service().fulfill_contract(
            contract, input.get("auth_service"), input.get("return_url"),
        )
        return FulfillContractMutation(signing_url=signing_url)


class Mutation:
    fulfill_contract = FulfillContractMutation.Field()
