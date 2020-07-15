import graphene
from django.utils.translation import ugettext_lazy as _
from graphene_django import DjangoObjectType
from graphql_jwt.decorators import login_required

from applications.models import BerthApplication
from berth_reservations.exceptions import VenepaikkaGraphQLError
from customers.models import CustomerProfile
from resources.schema import BerthNode
from users.utils import user_has_view_permission
from utils.enum import graphene_enum
from utils.schema import CountConnection

from ..enums import LeaseStatus
from ..models import BerthLease

LeaseStatusEnum = graphene_enum(LeaseStatus)


class BerthLeaseNode(DjangoObjectType):
    berth = graphene.Field(BerthNode, required=True)
    status = LeaseStatusEnum(required=True)
    customer = graphene.Field("customers.schema.ProfileNode", required=True)
    order = graphene.Field("payments.schema.OrderNode")
    is_active = graphene.Boolean(
        required=True,
        description="For a Lease to be active, it has to have `status == PAID`. "
        "\n\nIf the present date is before the season starts (10.6.2020), "
        "a lease will be active if it starts at the same date as the season. "
        "If the present date is during the season, a lease will be active if the "
        "dates `start date < today < end date`.",
    )

    class Meta:
        model = BerthLease
        interfaces = (graphene.relay.Node,)
        connection_class = CountConnection

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
