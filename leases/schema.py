import graphene
from django.utils.translation import ugettext_lazy as _
from graphene_django import DjangoConnectionField, DjangoObjectType
from graphql_jwt.decorators import login_required, superuser_required

from berth_reservations.exceptions import VenepaikkaGraphQLError
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
