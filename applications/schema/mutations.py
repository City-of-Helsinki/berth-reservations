import graphene
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from berth_reservations.exceptions import VenepaikkaGraphQLError
from customers.models import CustomerProfile
from leases.models import BerthLease, WinterStorageLease
from users.decorators import (
    change_permission_required,
    check_user_is_authorised,
    delete_permission_required,
    view_permission_required,
)
from users.utils import (
    is_customer,
    user_has_change_permission,
    user_has_delete_permission,
    user_has_view_permission,
)
from utils.relay import from_global_id, get_node_from_global_id
from utils.schema import update_object

from ..constants import MARKED_WS_SENDER, REJECT_BERTH_SENDER, UNMARKED_WS_SENDER
from ..enums import ApplicationAreaType, ApplicationStatus
from ..models import (
    BerthApplication,
    BerthSwitch,
    BerthSwitchReason,
    HarborChoice,
    WinterStorageApplication,
    WinterStorageAreaChoice,
)
from ..signals import application_rejected, application_saved
from .inputs import (
    BerthApplicationInput,
    BerthSwitchInput,
    UpdateBerthApplicationInput,
    WinterStorageApplicationInput,
)
from .types import BerthApplicationNode, HarborChoiceType, WinterStorageApplicationNode


class CreateBerthApplicationMutation(graphene.ClientIDMutation):
    class Input:
        berth_application = BerthApplicationInput(required=True)
        berth_switch = BerthSwitchInput()

    ok = graphene.Boolean()
    berth_application = graphene.Field(BerthApplicationNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **kwargs):
        from resources.models import BoatType
        from resources.schema import BerthNode, HarborNode

        application_data = kwargs.pop("berth_application")

        boat_type_id = application_data.pop("boat_type", None)
        if boat_type_id:
            application_data["boat_type"] = BoatType.objects.get(id=int(boat_type_id))

        switch_data = kwargs.pop("berth_switch", None)
        if switch_data:
            berth = get_node_from_global_id(
                info, switch_data.get("berth_id"), only_type=BerthNode
            )
            reason_id = switch_data.get("reason")
            reason = BerthSwitchReason.objects.get(id=reason_id) if reason_id else None
            berth_switch = BerthSwitch.objects.create(berth=berth, reason=reason)
            application_data["berth_switch"] = berth_switch

        choices = application_data.pop("choices", [])

        application = BerthApplication.objects.create(**application_data)

        for choice in choices:
            harbor = get_node_from_global_id(
                info, choice.get("harbor_id"), only_type=HarborNode
            )
            HarborChoice.objects.get_or_create(
                harbor=harbor, priority=choice.get("priority"), application=application
            )

        # Send notifications when all m2m relations are saved
        application_saved.send(sender="CreateBerthApplication", application=application)

        return CreateBerthApplicationMutation(berth_application=application)


class UpdateBerthApplication(graphene.ClientIDMutation):
    class Input(UpdateBerthApplicationInput):
        pass

    berth_application = graphene.Field(BerthApplicationNode)

    @classmethod
    def validate_application_status(cls, application, info, input):
        if application.status != ApplicationStatus.PENDING:
            if is_customer(info.context.user):
                raise VenepaikkaGraphQLError(
                    _("Cannot modify the application once it has been processed")
                )

            # If the input receives explicitly customerId: None
            if "customer_id" in input and input.get("customer_id") is None:
                raise VenepaikkaGraphQLError(
                    _("Customer cannot be disconnected from processed applications")
                )

    def get_nodes_to_check(info, **input):
        application = get_node_from_global_id(
            info, input.get("id"), only_type=BerthApplicationNode, nullable=True
        )
        return [application]

    @classmethod
    @check_user_is_authorised(
        get_nodes_to_check=get_nodes_to_check,
        model_checks=[
            user_has_view_permission(CustomerProfile, BerthLease),
            user_has_change_permission(BerthApplication),
        ],
    )
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        from customers.schema import ProfileNode

        application = get_node_from_global_id(
            info, input.pop("id"), only_type=BerthApplicationNode
        )

        cls.validate_application_status(application, info, input)

        # This allows for getting explicit None values
        if "customer_id" in input:
            customer_id = input.pop("customer_id", None)

            if is_customer(info.context.user):
                raise VenepaikkaGraphQLError(
                    _(
                        "A customer cannot modify the customer connected to the application"
                    )
                )

            input["customer"] = get_node_from_global_id(
                info, customer_id, only_type=ProfileNode, nullable=True
            )

        if remove_choices := input.pop("remove_choices", []):
            for choice_id in remove_choices:
                try:
                    choice = HarborChoice.objects.get(
                        id=from_global_id(choice_id, node_type=HarborChoiceType)
                    )
                    choice.delete()
                except HarborChoice.DoesNotExist:
                    pass

        if add_choices := input.pop("add_choices", []):
            for choice in add_choices:
                HarborChoice.objects.get_or_create(
                    harbor_id=from_global_id(choice.get("harbor_id")),
                    priority=choice.get("priority"),
                    application=application,
                )

        update_object(application, input)

        return UpdateBerthApplication(berth_application=application)


class DeleteBerthApplicationMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    def get_nodes_to_check(info, **input):
        application = get_node_from_global_id(
            info, input.get("id"), only_type=BerthApplicationNode, nullable=True
        )
        return [application]

    @classmethod
    @transaction.atomic
    @check_user_is_authorised(
        get_nodes_to_check=get_nodes_to_check,
        model_checks=[user_has_delete_permission(BerthApplication)],
    )
    def mutate_and_get_payload(cls, root, info, **input):
        application = get_node_from_global_id(
            info, input.pop("id"), only_type=BerthApplicationNode, nullable=False
        )

        application.delete()

        return DeleteBerthApplicationMutation()


class RejectBerthApplicationMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @change_permission_required(BerthApplication)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        application = get_node_from_global_id(
            info, input.get("id"), only_type=BerthApplicationNode, nullable=False
        )
        if hasattr(application, "lease"):
            raise VenepaikkaGraphQLError(_("Application has a lease"))

        application.status = ApplicationStatus.NO_SUITABLE_BERTHS
        application.save()

        application_rejected.send(sender=REJECT_BERTH_SENDER, application=application)

        return RejectBerthApplicationMutation()


class CreateWinterStorageApplicationMutation(graphene.ClientIDMutation):
    class Input:
        winter_storage_application = WinterStorageApplicationInput(required=True)

    winter_storage_application = graphene.Field(WinterStorageApplicationNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **kwargs):
        from resources.models import BoatType
        from resources.schema import WinterStorageAreaNode

        application_data = kwargs.pop("winter_storage_application")

        boat_type_id = application_data.pop("boat_type", None)
        if boat_type_id:
            application_data["boat_type"] = BoatType.objects.get(id=int(boat_type_id))

        chosen_areas = application_data.pop("chosen_areas", [])

        application = WinterStorageApplication.objects.create(**application_data)

        for choice in chosen_areas:
            winter_storage_area = get_node_from_global_id(
                info, choice.get("winter_area_id"), only_type=WinterStorageAreaNode
            )
            WinterStorageAreaChoice.objects.get_or_create(
                winter_storage_area=winter_storage_area,
                priority=choice.get("priority"),
                application=application,
            )

        application.area_type = application.resolve_area_type()
        application.save()

        # Send notifications when all m2m relations are saved
        sender = (
            UNMARKED_WS_SENDER
            if application.area_type == ApplicationAreaType.UNMARKED
            else MARKED_WS_SENDER
        )
        application_saved.send(sender=sender, application=application)

        return CreateWinterStorageApplicationMutation(
            winter_storage_application=application
        )


class UpdateWinterStorageApplication(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        customer_id = graphene.ID()

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

        customer_id = input.get("customer_id")

        if application.status != ApplicationStatus.PENDING and not customer_id:
            raise VenepaikkaGraphQLError(
                _("Customer cannot be disconnected from processed applications")
            )

        input["customer"] = get_node_from_global_id(
            info, customer_id, only_type=ProfileNode, nullable=True
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
    create_berth_application = CreateBerthApplicationMutation.Field()
    create_winter_storage_application = CreateWinterStorageApplicationMutation.Field()

    update_berth_application = UpdateBerthApplication.Field()
    delete_berth_application = DeleteBerthApplicationMutation.Field(
        description="**Requires permissions** to delete applications."
    )
    reject_berth_application = RejectBerthApplicationMutation.Field(
        description="**Requires permissions** to reject applications."
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
