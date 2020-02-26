import graphene
from django.utils.translation import ugettext_lazy as _
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType
from graphene_federation import extend, external
from graphql_jwt.decorators import login_required

from berth_reservations.exceptions import VenepaikkaGraphQLError

from .enums import InvoicingType
from .models import Boat, Company, CustomerProfile

InvoicingTypeEnum = graphene.Enum.from_enum(InvoicingType)

PROFILE_NODE_FIELDS = (
    "id",
    "invoicing_type",
    "comment",
    "company",
    "boats",
    "berth_applications",
    "berth_leases",
)


class BaseProfileFieldsMixin:
    """
    Mixin that stores the attributes that are exactly
    the same between ProfileNode and BerthProfileNode
    """

    invoicing_type = InvoicingTypeEnum(required=True)
    comment = graphene.String(required=True)


@extend(fields="id")
class ProfileNode(BaseProfileFieldsMixin, DjangoObjectType):
    """
    ProfileNode extended from the open-city-profile's ProfileNode.
    """

    class Meta:
        model = CustomerProfile
        fields = PROFILE_NODE_FIELDS
        interfaces = (relay.Node,)

    # explicitly mark shadowed ID field as external
    # otherwise, graphene-federation cannot catch it.
    id = external(relay.GlobalID())
    # TODO: maybe later investigate other approaches for this?
    # there is also this bug: if we include this ProfileNode
    # in some Query fields (e.g. profile = graphene.Field(ProfileNode))
    # graphene will also mark ID fields as "@external" on some
    # other random Node types (e.g. WinterStorageAreaNode)

    @login_required
    def __resolve_reference(self, info, **kwargs):
        user = info.context.user
        profile = relay.Node.get_node_from_global_id(info, self.id)
        if not profile:
            return None

        # TODO: implement proper permissions
        if user.is_superuser or user == profile.user:
            return profile
        else:
            raise VenepaikkaGraphQLError(
                _("You do not have permission to perform this action.")
            )


class BerthProfileNode(BaseProfileFieldsMixin, DjangoObjectType):
    """
    ProfileNode that only contains profile info stored in this service.
    """

    class Meta:
        model = CustomerProfile
        filter_fields = ("invoicing_type",)
        fields = PROFILE_NODE_FIELDS
        interfaces = (relay.Node,)

    @classmethod
    @login_required
    def get_node(cls, info, id):
        node = super().get_node(info, id)
        if not node:
            return None

        user = info.context.user
        # TODO: implement proper permissions
        if node.user == user or user.is_superuser:
            return node
        else:
            raise VenepaikkaGraphQLError(
                _("You do not have permission to perform this action.")
            )


class BoatNode(DjangoObjectType):
    class Meta:
        model = Boat


class CompanyType(DjangoObjectType):
    class Meta:
        model = Company
        fields = ("business_id", "name", "address", "postal_code", "city")


class Query:
    berth_profile = graphene.relay.Node.Field(BerthProfileNode)
    berth_profiles = DjangoFilterConnectionField(BerthProfileNode)

    @login_required
    def resolve_berth_profiles(self, info, **kwargs):
        # TODO: implement proper permissions
        if info.context.user.is_superuser:
            return CustomerProfile.objects.all()
        raise VenepaikkaGraphQLError(
            _("You do not have permission to perform this action.")
        )
