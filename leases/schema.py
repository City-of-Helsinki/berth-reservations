import django_filters
import graphene
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import ugettext_lazy as _
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphql_jwt.decorators import login_required

from applications.enums import ApplicationStatus
from applications.models import BerthApplication
from applications.new_schema import BerthApplicationNode
from berth_reservations.exceptions import VenepaikkaGraphQLError
from customers.models import CustomerProfile
from resources.schema import BerthNode
from users.decorators import (
    add_permission_required,
    delete_permission_required,
    view_permission_required,
)
from users.utils import user_has_view_permission
from utils.relay import get_node_from_global_id

from .enums import LeaseStatus
from .models import BerthLease

LeaseStatusEnum = graphene.Enum.from_enum(LeaseStatus)


class BerthLeaseNodeFilter(django_filters.FilterSet):
    order_by = django_filters.OrderingFilter(
        fields=(("created_at", "createdAt"),),
        label="Supports only `createdAt` and `-createdAt`.",
    )


class BerthLeaseNode(DjangoObjectType):
    berth = graphene.Field(BerthNode, required=True)
    status = LeaseStatusEnum(required=True)
    customer = graphene.Field("customers.schema.ProfileNode", required=True)

    class Meta:
        model = BerthLease
        interfaces = (graphene.relay.Node,)

    @classmethod
    @login_required
    def get_node(cls, info, id):
        node = super().get_node(info, id)
        if not node:
            return None

        user = info.context.user
        if (node.customer and node.customer.user == user) or user_has_view_permission(
            user, BerthLease, BerthApplication, CustomerProfile
        ):
            return node
        else:
            raise VenepaikkaGraphQLError(
                _("You do not have permission to perform this action.")
            )


class CreateBerthLeaseMutation(graphene.ClientIDMutation):
    class Input:
        application_id = graphene.ID(required=True)
        berth_id = graphene.ID(required=True)
        boat_id = graphene.ID()
        start_date = graphene.Date()
        end_date = graphene.Date()
        comment = graphene.String()

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
        berth = get_node_from_global_id(
            info, input.pop("berth_id"), only_type=BerthNode, nullable=False,
        )

        if not application.customer:
            raise VenepaikkaGraphQLError(
                _("Application must be connected to an existing customer first")
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
            raise VenepaikkaGraphQLError(e)

        application.status = ApplicationStatus.OFFER_GENERATED
        application.save()

        return CreateBerthLeaseMutation(berth_lease=lease)


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


class Query:
    berth_lease = graphene.relay.Node.Field(BerthLeaseNode)
    berth_leases = DjangoFilterConnectionField(
        BerthLeaseNode,
        filterset_class=BerthLeaseNodeFilter,
        description="`BerthLeases` are ordered by `createdAt` in ascending order by default.",
    )

    @view_permission_required(BerthLease, BerthApplication, CustomerProfile)
    def resolve_berth_leases(self, info, **kwargs):
        return (
            BerthLease.objects.select_related(
                "application",
                "application__customer",
                "berth",
                "berth__pier",
                "berth__pier__harbor",
            )
            .prefetch_related("application__customer__boats")
            .order_by("created_at")
        )


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

    delete_berth_lease = DeleteBerthLeaseMutation.Field(
        description="Deletes a `BerthLease` object."
        "\n\nIt **only** works for leases that haven't been assigned, i.e., leases that have "
        '\n`berth_lease.status == "DRAFTED"`.'
        "\n\n**Requires permissions** to access leases."
        "\n\nErrors:"
        "\n* A berth lease that is not `DRAFTED` anymore is passed"
        "\n* The passed lease ID doesn't exist"
    )
