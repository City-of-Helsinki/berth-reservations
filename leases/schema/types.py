import graphene
from graphene_django import DjangoObjectType
from graphql_jwt.decorators import login_required

from applications.models import BerthApplication, WinterStorageApplication
from customers.models import CustomerProfile
from resources.schema import BerthNode, WinterStorageAreaNode, WinterStoragePlaceNode
from utils.enum import graphene_enum
from utils.relay import return_node_if_user_has_permissions
from utils.schema import CountConnection

from ..enums import LeaseStatus
from ..models import BerthLease, WinterStorageLease

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
        return return_node_if_user_has_permissions(
            node, info.context.user, BerthLease, BerthApplication, CustomerProfile
        )


class WinterStorageLeaseNode(DjangoObjectType):
    place = graphene.Field(WinterStoragePlaceNode)
    area = graphene.Field(WinterStorageAreaNode)
    status = LeaseStatusEnum(required=True)
    customer = graphene.Field("customers.schema.ProfileNode", required=True)
    order = graphene.Field("payments.schema.OrderNode")

    class Meta:
        model = WinterStorageLease
        interfaces = (graphene.relay.Node,)
        connection_class = CountConnection

    @classmethod
    @login_required
    def get_node(cls, info, id):
        node = super().get_node(info, id)
        return return_node_if_user_has_permissions(
            node,
            info.context.user,
            WinterStorageLease,
            WinterStorageApplication,
            CustomerProfile,
        )
