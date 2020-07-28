import graphene
from django.db import transaction

from customers.models import CustomerProfile
from leases.models import BerthLease, WinterStorageLease
from users.decorators import (
    change_permission_required,
    delete_permission_required,
    view_permission_required,
)
from utils.relay import get_node_from_global_id
from utils.schema import update_object

from ..models import BerthApplication, WinterStorageApplication
from .types import BerthApplicationNode, WinterStorageApplicationNode


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
        input["customer"] = get_node_from_global_id(
            info, input.pop("customer_id"), only_type=ProfileNode
        )

        update_object(application, input)

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


class WinterStorageApplicationInput:
    # TODO: the required has to be removed once more fields are added
    customer_id = graphene.ID(required=True)


class UpdateWinterStorageApplication(graphene.ClientIDMutation):
    class Input(WinterStorageApplicationInput):
        id = graphene.ID(required=True)

    winter_storage_application = graphene.Field(WinterStorageApplicationNode)

    @classmethod
    @view_permission_required(CustomerProfile, WinterStorageLease)
    @change_permission_required(WinterStorageApplication)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        from customers.schema import ProfileNode

        application = get_node_from_global_id(
            info, input.pop("id"), only_type=WinterStorageApplicationNode
        )
        input["customer"] = get_node_from_global_id(
            info, input.pop("customer_id"), only_type=ProfileNode
        )

        update_object(application, input)

        return UpdateWinterStorageApplication(winter_storage_application=application)


class DeleteWinterStorageApplicationMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(WinterStorageApplication)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        application = get_node_from_global_id(
            info,
            input.get("id"),
            only_type=WinterStorageApplicationNode,
            nullable=False,
        )

        application.delete()

        return DeleteBerthApplicationMutation()


class Mutation:
    update_berth_application = UpdateBerthApplication.Field()
    delete_berth_application = DeleteBerthApplicationMutation.Field(
        description="**Requires permissions** to delete applications."
    )

    update_winter_storage_application = UpdateWinterStorageApplication.Field(
        description="Updates a `WinterStorageApplication`."
        "\n\n**Requires permissions** to update applications."
        "\n\nErrors:"
        "\n* The passed application doesn't exist"
        "\n* The passed customer doesn't exist"
    )
    delete_winter_storage_application = DeleteWinterStorageApplicationMutation.Field(
        description="Deletes a `WinterStorageApplication`."
        "\n\n**Requires permissions** to delete applications."
        "\n\nErrors:"
        "\n* The passed application doesn't exist"
    )
