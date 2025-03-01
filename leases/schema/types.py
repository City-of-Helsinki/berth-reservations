from typing import List

import graphene
from graphene_django import DjangoObjectType
from graphql_jwt.decorators import login_required

from applications.models import BerthApplication, WinterStorageApplication
from contracts.schema import WinterStorageContractNode
from contracts.schema.types import BerthContractNode
from customers.models import CustomerProfile
from payments.enums import OfferStatus
from payments.models import BerthSwitchOffer
from resources.schema import BerthNode, WinterStoragePlaceNode, WinterStorageSectionNode
from utils.relay import (
    return_node_if_user_has_permissions,
    return_queryset_if_user_has_permissions,
)
from utils.schema import CountConnection

from ..enums import LeaseStatus
from ..models import BerthLease, WinterStorageLease
from ..stickers import get_ws_sticker_season

LeaseStatusEnum = graphene.Enum.from_enum(LeaseStatus)


class BerthLeaseNode(DjangoObjectType):
    berth = graphene.Field(BerthNode, required=True)
    status = LeaseStatusEnum(required=True)
    customer = graphene.Field("customers.schema.ProfileNode", required=True)
    last_offered_to = graphene.Field(
        "customers.schema.ProfileNode",
        description="The customer profile from the latest switch offer with `status == OFFERED`.",
    )
    order = graphene.Field("payments.schema.OrderNode")
    contract = graphene.Field(BerthContractNode)
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
    def get_queryset(cls, queryset, info):
        user = info.context.user
        return return_queryset_if_user_has_permissions(
            queryset, user, BerthLease, BerthApplication, CustomerProfile
        )

    @classmethod
    @login_required
    def get_node(cls, info, id):
        node = super().get_node(info, id)
        return return_node_if_user_has_permissions(
            node, info.context.user, BerthLease, BerthApplication, CustomerProfile
        )

    def resolve_customer(self, info, **kwargs):
        return info.context.customer_loader.load(self.customer_id)

    def resolve_last_offered_to(self, info):
        switch_offers_for_leases_loader = info.context.switch_offers_for_leases_loader
        customer_loader = info.context.customer_loader

        def __get_customer_from_offers(offers: List[BerthSwitchOffer]):
            latest_pending_offer = next(
                (
                    offer
                    for offer in reversed(offers)
                    if offer.status == OfferStatus.OFFERED
                ),
                None,
            )
            if not latest_pending_offer:
                return None
            return customer_loader.load(latest_pending_offer.customer_id)

        return switch_offers_for_leases_loader.load(self.id).then(
            lambda offers: (
                __get_customer_from_offers(offers)
                if offers and len(offers) > 0
                else None
            )
        )


class WinterStorageLeaseNode(DjangoObjectType):
    place = graphene.Field(WinterStoragePlaceNode)
    section = graphene.Field(WinterStorageSectionNode)
    status = LeaseStatusEnum(required=True)
    customer = graphene.Field("customers.schema.ProfileNode", required=True)
    order = graphene.Field("payments.schema.OrderNode")
    contract = graphene.Field(WinterStorageContractNode)
    is_active = graphene.Boolean(
        required=True,
        description="For a Lease to be active, it has to have `status == PAID`. "
        "\n\nIf the present date is before the season starts (15.9.2020), "
        "a lease will be active if it starts at the same date as the season. "
        "If the present date is during the season, a lease will be active if the "
        "dates `start date < today < end date`.",
    )
    sticker_season = graphene.String()

    class Meta:
        model = WinterStorageLease
        interfaces = (graphene.relay.Node,)
        connection_class = CountConnection

    def resolve_sticker_season(self, info, **kwargs):
        season = get_ws_sticker_season(self.start_date)
        return season.replace("_", "/")

    @classmethod
    @login_required
    def get_queryset(cls, queryset, info):
        user = info.context.user
        return return_queryset_if_user_has_permissions(
            queryset,
            user,
            WinterStorageLease,
            WinterStorageApplication,
            CustomerProfile,
        )

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


class FailedInstanceType(graphene.ObjectType):
    id = graphene.ID(required=True)
    error = graphene.String()


class SendExistingInvoicesPreviewType(graphene.ObjectType):
    expected_leases = graphene.Int(required=True)
