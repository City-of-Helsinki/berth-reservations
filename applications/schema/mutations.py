import graphene
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from berth_reservations.exceptions import VenepaikkaGraphQLError
from customers.models import Boat, CustomerProfile
from leases.models import BerthLease, WinterStorageLease
from users.decorators import (
    change_permission_required,
    check_user_is_authorised,
    delete_permission_required,
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
from ..enums import ApplicationAreaType, ApplicationPriority, ApplicationStatus
from ..models import (
    BerthApplication,
    BerthApplicationChange,
    BerthSwitch,
    BerthSwitchReason,
    HarborChoice,
    WinterStorageApplication,
    WinterStorageApplicationChange,
    WinterStorageAreaChoice,
)
from ..signals import application_rejected, application_saved
from .inputs import (
    BerthApplicationInput,
    BerthSwitchInput,
    UpdateBerthApplicationInput,
    UpdateWinterStorageApplicationInput,
    WinterStorageApplicationInput,
)
from .types import BerthApplicationNode, WinterStorageApplicationNode


def _validate_boat_fields_common(application_data):
    if "boat_id" in application_data:
        if any(
            field.startswith("boat_") and field != "boat_id"
            for field in application_data
        ):
            raise VenepaikkaGraphQLError(
                _('Cannot use both boat ID and other boat field(s) at the same time"')
            )


def _validate_boat_fields_on_create(application_data):
    _validate_boat_fields_common(application_data)

    # either all of these xor boat_id is required on create mutations
    required_boat_fields = ["boat_type", "boat_length", "boat_width"]

    if "boat_id" not in application_data and not all(
        field in application_data for field in required_boat_fields
    ):
        raise VenepaikkaGraphQLError(
            'Either "boatId" or "boatType", "boatLength" and "boatWidth" are required"'
        )


def _handle_boat_on_create(application_data, info) -> Boat:
    from customers.schema import BoatNode

    _validate_boat_fields_on_create(application_data)

    if "boat_id" in application_data:
        boat = get_node_from_global_id(
            info, application_data.pop("boat_id"), only_type=BoatNode, nullable=False
        )
    else:
        boat_data = _get_boat_data(application_data)

        if is_customer(info.context.user):
            boat_data["owner"] = info.context.user.customer

        boat = Boat.objects.create(**boat_data)

    return boat


def _handle_boat_on_update(application, application_data, info) -> Boat:
    from customers.schema import BoatNode

    _validate_boat_fields_common(application_data)

    if "boat_id" in application_data:
        boat = get_node_from_global_id(
            info, application_data.pop("boat_id"), only_type=BoatNode
        )
        boat_data = {}
    else:
        boat = application.boat
        boat_data = _get_boat_data(application_data)

    if application_data.get("customer") and not boat.owner:
        # an anonymous application is begin assigned to a customer,
        # assign the boat as well
        boat_data["owner"] = application_data["customer"]

    if boat_data:
        update_object(boat, boat_data)

    return boat


def _get_boat_data(application_data):
    from resources.models import BoatType

    boat_fields = [
        "registration_number",
        "name",
        "model",
        "length",
        "width",
        "draught",
        "weight",
        "propulsion",
        "hull_material",
        "intended_use",
        "is_inspected",
        "is_insured",
    ]
    boat_data = {
        boat_field: application_data.pop(f"boat_{boat_field}")
        for boat_field in boat_fields
        if f"boat_{boat_field}" in application_data
    }

    if "boat_type" in application_data:
        boat_data["boat_type"] = BoatType.objects.get(
            id=int(application_data.pop("boat_type"))
        )

    return boat_data


class CreateBerthApplicationMutation(graphene.ClientIDMutation):
    class Input:
        berth_application = BerthApplicationInput(required=True)
        berth_switch = BerthSwitchInput()

    ok = graphene.Boolean()
    berth_application = graphene.Field(BerthApplicationNode)

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **kwargs):
        from resources.schema import BerthNode, HarborNode

        application_data = kwargs.pop("berth_application")

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
        application_data["boat"] = _handle_boat_on_create(application_data, info)

        if is_customer(info.context.user):
            application_data["customer"] = info.context.user.customer

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

        old_choices = set(application.harborchoice_set.all())

        if remove_choices := input.pop("remove_choices", []):
            # Delete the choices based on their priority (passed as input)
            application.harborchoice_set.filter(priority__in=remove_choices).delete()

            # For the ones left, re-calculate their priority
            for new_priority, choice in enumerate(
                application.harborchoice_set.order_by("priority"), start=1
            ):
                choice.priority = new_priority
                choice.save()

        if add_choices := input.pop("add_choices", []):
            for choice in add_choices:
                HarborChoice.objects.get_or_create(
                    harbor_id=from_global_id(choice.get("harbor_id")),
                    priority=choice.get("priority"),
                    application=application,
                )

        new_choices = set(application.harborchoice_set.all())

        if old_choices != new_choices:
            old_choices = "\n".join([str(choice) for choice in old_choices])
            new_choices = "\n".join([str(choice) for choice in new_choices])
            change_list = (
                f"Old harbor choices:\n{old_choices}\n\n"
                f"New harbor choices:\n{new_choices}"
            )
            BerthApplicationChange.objects.create(
                application=application, change_list=change_list
            )

        input["boat"] = _handle_boat_on_update(application, input, info)

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


class ExtendBerthApplicationMutation(graphene.ClientIDMutation):
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
        model_checks=[user_has_change_permission(BerthApplication)],
    )
    def mutate_and_get_payload(cls, root, info, **input):
        application = get_node_from_global_id(
            info, input.pop("id"), only_type=BerthApplicationNode, nullable=False
        )

        if application.status != ApplicationStatus.NO_SUITABLE_BERTHS:
            raise VenepaikkaGraphQLError(
                _("Cannot extend applications that have not been rejected")
            )

        application.status = ApplicationStatus.PENDING
        application.priority = ApplicationPriority.LOW
        application.save()

        return ExtendBerthApplicationMutation()


class CreateWinterStorageApplicationMutation(graphene.ClientIDMutation):
    class Input:
        winter_storage_application = WinterStorageApplicationInput(required=True)

    winter_storage_application = graphene.Field(WinterStorageApplicationNode)

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **kwargs):
        from resources.schema import WinterStorageAreaNode

        application_data = kwargs.pop("winter_storage_application")

        chosen_areas = application_data.pop("chosen_areas", [])

        application_data["boat"] = _handle_boat_on_create(application_data, info)

        if is_customer(info.context.user):
            application_data["customer"] = info.context.user.customer

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
    class Input(UpdateWinterStorageApplicationInput):
        pass

    winter_storage_application = graphene.Field(WinterStorageApplicationNode)

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
            info, input.get("id"), only_type=WinterStorageApplicationNode, nullable=True
        )
        return [application]

    @classmethod
    @check_user_is_authorised(
        get_nodes_to_check=get_nodes_to_check,
        model_checks=[
            user_has_view_permission(CustomerProfile, WinterStorageLease),
            user_has_change_permission(WinterStorageApplication),
        ],
    )
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        from customers.schema import ProfileNode

        application = get_node_from_global_id(
            info, input.pop("id"), only_type=WinterStorageApplicationNode
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

        old_choices = set(application.winterstorageareachoice_set.all())

        if remove_choices := input.pop("remove_choices", []):
            # Delete the choices based on their priority (passed as input)
            application.winterstorageareachoice_set.filter(
                priority__in=remove_choices
            ).delete()

            # For the ones left, re-calculate their priority
            for new_priority, choice in enumerate(
                application.winterstorageareachoice_set.order_by("priority"), start=1
            ):
                choice.priority = new_priority
                choice.save()

        if add_choices := input.pop("add_choices", []):
            for choice in add_choices:
                WinterStorageAreaChoice.objects.get_or_create(
                    winter_storage_area_id=from_global_id(choice.get("winter_area_id")),
                    priority=choice.get("priority"),
                    application=application,
                )

        new_choices = set(application.winterstorageareachoice_set.all())

        if old_choices != new_choices:
            old_choices = "\n".join([str(choice) for choice in old_choices])
            new_choices = "\n".join([str(choice) for choice in new_choices])
            change_list = (
                f"Old area choices:\n{old_choices}\n\n"
                f"New area choices:\n{new_choices}"
            )
            WinterStorageApplicationChange.objects.create(
                application=application, change_list=change_list
            )

        input["boat"] = _handle_boat_on_update(application, input, info)

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
    extend_berth_application = ExtendBerthApplicationMutation.Field(
        description="Extends the validity of the application by moving it "
        "from `NO SUITABLE BERTHS` status to `PENDING`"
        "\n\n**Requires permissions** to update applications."
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
