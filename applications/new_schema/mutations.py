import graphene
from django.db import transaction

from applications.models import BerthApplication
from customers.models import CustomerProfile
from leases.models import BerthLease
from users.decorators import (
    change_permission_required,
    delete_permission_required,
    view_permission_required,
)
from utils.relay import get_node_from_global_id

from .types import BerthApplicationNode


class BerthApplicationInput:
    # TODO: the required has to be removed once more fields are added
    customer_id = graphene.ID(required=True)


class UpdateBerthApplication(graphene.ClientIDMutation):
    class Input(BerthApplicationInput):
        id = graphene.ID(required=True)

    berth_application = graphene.Field(BerthApplicationNode)

    @classmethod
    @view_permission_required(CustomerProfile, BerthLease)
    @change_permission_required(BerthApplication)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        from customers.schema import ProfileNode

        application = get_node_from_global_id(
            info, input.pop("id"), only_type=BerthApplicationNode
        )
        customer = get_node_from_global_id(
            info, input.pop("customer_id"), only_type=ProfileNode
        )

        application.customer = customer
        application.save()

        return UpdateBerthApplication(berth_application=application)


class DeleteBerthApplicationMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(BerthApplication)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        application = get_node_from_global_id(
            info, input.get("id"), only_type=BerthApplicationNode, nullable=False
        )

        application.delete()

        return DeleteBerthApplicationMutation()


class Mutation:
    update_berth_application = UpdateBerthApplication.Field()
    delete_berth_application = DeleteBerthApplicationMutation.Field(
        description="**Requires permissions** to delete applications."
    )
