import graphene
from django.db import transaction
from django.utils.translation import ugettext_lazy as _
from graphene_django import DjangoConnectionField, DjangoObjectType
from graphql_jwt.decorators import login_required, superuser_required
from graphql_relay import from_global_id

from applications.models import BerthApplication
from berth_reservations.exceptions import VenepaikkaGraphQLError
from customers.models import Boat
from resources.models import Berth
from resources.schema import BerthNode

from .enums import LeaseStatus
from .models import BerthLease

LeaseStatusEnum = graphene.Enum.from_enum(LeaseStatus)


class BerthLeaseNode(DjangoObjectType):
    berth = graphene.Field(BerthNode)
    status = LeaseStatusEnum()

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
        # TODO: implement proper permissions
        if (node.customer and node.customer.user == user) or user.is_superuser:
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
    @login_required
    @superuser_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        # TODO: Should check if the user has permissions to
        # delete the specific resource
        application_id = from_global_id(input.pop("application_id"))[1]
        berth_id = from_global_id(input.pop("berth_id"))[1]

        try:
            application = BerthApplication.objects.get(pk=application_id)
            berth = Berth.objects.get(pk=berth_id)
        except (BerthApplication.DoesNotExist, Berth.DoesNotExist) as e:
            raise VenepaikkaGraphQLError(e)

        if not application.customer:
            raise VenepaikkaGraphQLError(
                _("Application must be connected to an existing customer first")
            )

        input["application"] = application
        input["berth"] = berth
        input["customer"] = application.customer

        if input.get("boat_id", False):
            boat = Boat.objects.filter(pk=input.pop("boat_id")).first()

            if boat.owner.id != input["customer"].id:
                raise VenepaikkaGraphQLError(
                    _("Boat does not belong to the same customer as the Application")
                )

            input["boat"] = boat

        lease = BerthLease.objects.create(**input)

        return CreateBerthLeaseMutation(berth_lease=lease)


class Query:
    berth_lease = graphene.relay.Node.Field(BerthLeaseNode)
    berth_leases = DjangoConnectionField(BerthLeaseNode)

    @login_required
    @superuser_required
    # TODO: Should check if the user has permissions to access these objects
    def resolve_berth_leases(self, info, **kwargs):
        return BerthLease.objects.select_related(
            "application",
            "application__customer",
            "berth",
            "berth__pier",
            "berth__pier__harbor",
        ).prefetch_related("application__customer__boats")


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
