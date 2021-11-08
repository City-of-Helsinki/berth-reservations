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
)
from users.utils import (
    is_customer,
    user_has_add_permission,
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


def get_application_customer(info):
    if is_customer(info.context.user):
        # customer-created applications are always linked to the current customer.
        # If admins create applications, customer should be assigned later.
        if not info.context.user.customer:
            raise VenepaikkaGraphQLError(
                _("Customer has no CustomerProfile, can not create application")
            )
        return info.context.user.customer
    else:
        return None


def assign_boat(application_data, info):
    from customers.schema import BoatNode

    if "boat_id" in application_data:
        if boat_id := application_data.pop("boat_id", None):
            application_data["boat"] = get_node_from_global_id(
                info, boat_id, only_type=BoatNode, nullable=False
            )
        else:
            application_data["boat"] = None


def assign_boat_type(application_data):
    from resources.models import BoatType

    if "boat_type" in application_data:
        if boat_type_id := application_data.pop("boat_type", None):
            application_data["boat_type"] = BoatType.objects.get(id=int(boat_type_id))
        else:
            application_data["boat_type"] = None


class CreateBerthApplicationMutation(graphene.ClientIDMutation):
    class Input:
        berth_application = BerthApplicationInput(required=True)
        berth_switch = BerthSwitchInput()

    ok = graphene.Boolean()
    berth_application = graphene.Field(BerthApplicationNode)

    def get_nodes_to_check(info, **input):
        # Application does not exist yet. Check if the logged in user has permission to
        # their ProfileNode.
        if not info.context.user:
            raise VenepaikkaGraphQLError(_("Login required"))
        return [info.context.user]

    @classmethod
    @check_user_is_authorised(
        get_nodes_to_check=get_nodes_to_check,
        model_checks=[user_has_add_permission(BerthApplication)],
    )
    @transaction.atomic
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

        application_data["customer"] = get_application_customer(info)
        assign_boat(application_data, info)

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

        # don't change customer field in any way if no customer_id in input.
        if "customer_id" in input:
            customer_id = input.pop("customer_id", None)
            if customer_id:
                customer = get_node_from_global_id(
                    info, customer_id, only_type=ProfileNode, nullable=True
                )

                if is_customer(info.context.user):
                    # the checks here are defensive programming - the checks in
                    # check_user_is_authorised and get_node_from_global_id should catch these situations
                    if (
                        application.customer
                        and info.context.user.customer != application.customer
                    ):
                        raise VenepaikkaGraphQLError(
                            _(
                                "Unexpected: A customer cannot modify application by another customer"
                            )
                        )
                    if info.context.user.customer != customer:
                        raise VenepaikkaGraphQLError(
                            _(
                                "Unexpected: A customer cannot set the customer of application to another customer"
                            )
                        )

                input["customer"] = customer
            else:
                if is_customer(info.context.user) and application.customer:
                    raise VenepaikkaGraphQLError(
                        _(
                            "A customer cannot unset the customer connected to the application"
                        )
                    )
                input["customer"] = None

        cls.handle_harbor_choices(application, input)

        assign_boat_type(input)
        assign_boat(input, info)
        if input.get("boat"):
            # if any of the new_boat_fields have non-empty values in input, that will result
            # in validation error when saving the application.
            application.clear_new_boat_fields()

        update_object(application, input)

        return UpdateBerthApplication(berth_application=application)

    @classmethod
    def handle_harbor_choices(cls, application, input):
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

    def get_nodes_to_check(info, **input):
        # Application does not exist yet. Check if the logged in user has permission to
        # their ProfileNode.
        if not info.context.user:
            raise VenepaikkaGraphQLError(_("Login required"))
        return [info.context.user]

    @classmethod
    @check_user_is_authorised(
        get_nodes_to_check=get_nodes_to_check,
        model_checks=[user_has_add_permission(BerthApplication)],
    )
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **kwargs):
        from resources.models import BoatType
        from resources.schema import WinterStorageAreaNode

        application_data = kwargs.pop("winter_storage_application")

        boat_type_id = application_data.pop("boat_type", None)
        if boat_type_id:
            application_data["boat_type"] = BoatType.objects.get(id=int(boat_type_id))

        chosen_areas = application_data.pop("chosen_areas", [])

        application_data["customer"] = get_application_customer(info)
        assign_boat(application_data, info)
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
        application.refresh_from_db()  # if some field was assigned a float value, load the actual decimal value from db
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

        assign_boat_type(input)
        assign_boat(input, info)
        if input.get("boat"):
            # if any of the new_boat_fields have non-empty values in input, that will result
            # in validation error when saving the application.
            application.clear_new_boat_fields()

        update_object(application, input)
        application.refresh_from_db()
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
