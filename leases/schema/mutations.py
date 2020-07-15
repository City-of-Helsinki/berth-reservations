import graphene
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import ugettext_lazy as _

from applications.enums import ApplicationStatus
from applications.models import BerthApplication
from applications.new_schema import BerthApplicationNode
from berth_reservations.exceptions import VenepaikkaGraphQLError
from customers.models import CustomerProfile
from resources.schema import BerthNode
from users.decorators import (
    add_permission_required,
    change_permission_required,
    delete_permission_required,
    view_permission_required,
)
from utils.relay import get_node_from_global_id
from utils.schema import update_object

from ..enums import LeaseStatus
from ..models import BerthLease
from .types import BerthLeaseNode


class BerthLeaseInput:
    boat_id = graphene.ID()
    start_date = graphene.Date()
    end_date = graphene.Date()
    comment = graphene.String()


class CreateBerthLeaseMutation(graphene.ClientIDMutation):
    class Input(BerthLeaseInput):
        application_id = graphene.ID(required=True)
        berth_id = graphene.ID(required=True)

    berth_lease = graphene.Field(BerthLeaseNode)

    @classmethod
    @view_permission_required(BerthApplication, CustomerProfile)
    @add_permission_required(BerthLease)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        application = get_node_from_global_id(
            info,
            input.pop("application_id"),
            only_type=BerthApplicationNode,
            nullable=False,
        )

        if not application.customer:
            raise VenepaikkaGraphQLError(
                _("Application must be connected to an existing customer first")
            )

        berth = get_node_from_global_id(
            info, input.pop("berth_id"), only_type=BerthNode, nullable=False,
        )

        input["application"] = application
        input["berth"] = berth
        input["customer"] = application.customer

        if input.get("boat_id", False):
            from customers.schema import BoatNode

            boat = get_node_from_global_id(
                info, input.pop("boat_id"), only_type=BoatNode, nullable=False,
            )

            if boat.owner.id != input["customer"].id:
                raise VenepaikkaGraphQLError(
                    _("Boat does not belong to the same customer as the Application")
                )

            input["boat"] = boat

        try:
            lease = BerthLease.objects.create(**input)
        except ValidationError as e:
            # Flatten all the error messages on a single list
            errors = sum(e.message_dict.values(), [])
            raise VenepaikkaGraphQLError(errors)

        application.status = ApplicationStatus.OFFER_GENERATED
        application.save()

        return CreateBerthLeaseMutation(berth_lease=lease)


class UpdateBerthLeaseMutation(graphene.ClientIDMutation):
    class Input(BerthLeaseInput):
        id = graphene.ID(required=True)
        application_id = graphene.ID()

    berth_lease = graphene.Field(BerthLeaseNode)

    @classmethod
    @change_permission_required(BerthLease)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        lease = get_node_from_global_id(
            info, input.pop("id"), only_type=BerthLeaseNode, nullable=False,
        )
        application_id = input.get("application_id")

        if application_id:
            # If the application id was passed, raise an error if it doesn't exist
            application = get_node_from_global_id(
                info, application_id, only_type=BerthApplicationNode, nullable=False,
            )
            if not application.customer:
                raise VenepaikkaGraphQLError(
                    _("Application must be connected to an existing customer first")
                )
            input["application"] = application
            input["customer"] = application.customer

        if input.get("boat_id", False):
            from customers.schema import BoatNode

            boat = get_node_from_global_id(
                info, input.pop("boat_id"), only_type=BoatNode, nullable=False,
            )

            if boat.owner.id != input["customer"].id:
                raise VenepaikkaGraphQLError(
                    _("Boat does not belong to the same customer as the Application")
                )

            input["boat"] = boat

        try:
            update_object(lease, input)
        except ValidationError as e:
            # Flatten all the error messages on a single list
            errors = sum(e.message_dict.values(), [])
            raise VenepaikkaGraphQLError(errors)

        return UpdateBerthLeaseMutation(berth_lease=lease)


class DeleteBerthLeaseMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(BerthLease)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        lease = get_node_from_global_id(
            info, input.pop("id"), only_type=BerthLeaseNode, nullable=False,
        )

        if lease.status != LeaseStatus.DRAFTED:
            raise VenepaikkaGraphQLError(
                _(f"Lease object is not DRAFTED anymore: {lease.status}")
            )

        if lease.application:
            lease.application.status = ApplicationStatus.PENDING
            lease.application.save()

        lease.delete()

        return DeleteBerthLeaseMutation()


class Mutation:
    create_berth_lease = CreateBerthLeaseMutation.Field(
        description="Creates a `BerthLease` associated with the `BerthApplication` and `Berth` passed. "
        "The lease is associated with the `CustomerProfile` that owns the application."
        "\n\n**Requires permissions** to access applications."
        "\n\nLeases have default start and end dates: 10.6. - 14.9. If a lease object is being created before 10.6, "
        "then the dates are in the same year. If the object is being created between those dates, "
        "then the start date is the date of creation and end date is 14.9 of the same year. "
        "If the object is being created after 14.9, then the dates are from next year."
        "\n\nErrors:"
        "\n* An application without a customer associated is passed"
        "\n* A boat is passed and the owner of the boat differs from the owner of the application"
    )

    update_berth_lease = UpdateBerthLeaseMutation.Field(
        description="Updates a `BerthLease` object."
        "\n\n**Requires permissions** to edit leases."
        "\n\nErrors:"
        "\n* An application without a customer associated is passed"
        "\n* A boat is passed and the owner of the boat differs from the owner of the application"
    )

    delete_berth_lease = DeleteBerthLeaseMutation.Field(
        description="Deletes a `BerthLease` object."
        "\n\nIt **only** works for leases that haven't been assigned, i.e., leases that have "
        '\n`berth_lease.status == "DRAFTED"`.'
        "\n\n**Requires permissions** to access leases."
        "\n\nErrors:"
        "\n* A berth lease that is not `DRAFTED` anymore is passed"
        "\n* The passed lease ID doesn't exist"
    )
