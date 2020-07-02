import django_filters
import graphene
from django.utils.translation import ugettext_lazy as _
from graphene import relay
from graphene_django import DjangoConnectionField, DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphene_federation import extend, external
from graphql_jwt.decorators import login_required

from applications.models import BerthApplication
from applications.new_schema import BerthApplicationNode
from berth_reservations.exceptions import VenepaikkaGraphQLError
from leases.models import BerthLease
from leases.schema import BerthLeaseNode
from users.utils import user_has_view_permission
from utils.enum import graphene_enum
from utils.relay import get_node_from_global_id
from utils.schema import CountConnection

from ..enums import BoatCertificateType, InvoicingType, OrganizationType
from ..models import Boat, BoatCertificate, CustomerProfile, Organization

InvoicingTypeEnum = graphene_enum(InvoicingType)
OrganizationTypeEnum = graphene_enum(OrganizationType)
BoatCertificateTypeEnum = graphene_enum(BoatCertificateType)


class BoatCertificateNode(DjangoObjectType):
    certificate_type = BoatCertificateTypeEnum(required=True)

    class Meta:
        model = BoatCertificate
        interfaces = (relay.Node,)
        connection_class = CountConnection

    def resolve_file(self, info, **kwargs):
        return info.context.build_absolute_uri(self.file.url) if self.file else None


class BoatNode(DjangoObjectType):
    owner = graphene.Field("customers.schema.ProfileNode", required=True)
    certificates = graphene.List("customers.schema.BoatCertificateNode", required=True)
    length = graphene.Decimal(required=True)
    width = graphene.Decimal(required=True)
    draught = graphene.Decimal()

    class Meta:
        model = Boat
        interfaces = (relay.Node,)
        connection_class = CountConnection

    def resolve_certificates(self, info):
        return self.certificates.all()


class OrganizationNode(DjangoObjectType):
    customer = graphene.Field("customers.schema.ProfileNode", required=True)
    organization_type = OrganizationTypeEnum(required=True)

    class Meta:
        model = Organization
        interfaces = (relay.Node,)
        fields = ("business_id", "name", "address", "postal_code", "city")
        connection_class = CountConnection


PROFILE_NODE_FIELDS = (
    "id",
    "invoicing_type",
    "comment",
    "organization",
    "boats",
    "berth_applications",
    "berth_leases",
    "orders",
)


class BerthApplicationFilter(django_filters.FilterSet):
    order_by = django_filters.OrderingFilter(
        fields=(("created_at", "createdAt"),),
        label="Supports `createdAt` and `-createdAt`.",
    )


class BaseProfileFieldsMixin:
    """
    Mixin that stores the attributes that are exactly
    the same between ProfileNode and BerthProfileNode

    BEWARE: since ProfileNode is extended, none of its
    fields could be non-nullable (i.e. required=True),
    because then the entire ProfileNode will be null at
    the federation level, if the profile object has no
    object in our database.
    """

    invoicing_type = InvoicingTypeEnum()
    comment = graphene.String()
    organization = graphene.Field(OrganizationNode)
    boats = DjangoConnectionField(BoatNode)
    berth_applications = DjangoFilterConnectionField(
        BerthApplicationNode,
        filterset_class=BerthApplicationFilter,
        description="`BerthApplications` are ordered by `createdAt` in ascending order by default.",
    )
    berth_leases = DjangoConnectionField(BerthLeaseNode)
    orders = DjangoConnectionField("payments.schema.OrderNode")

    def resolve_berth_applications(self, info, **kwargs):
        return self.berth_applications.order_by("created_at")


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
        profile = get_node_from_global_id(info, self.id, only_type=ProfileNode)
        if not profile:
            return None

        if profile.user == user or user_has_view_permission(
            user, CustomerProfile, BerthApplication, BerthLease
        ):
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
        connection_class = CountConnection

    @classmethod
    @login_required
    def get_node(cls, info, id):
        node = super().get_node(info, id)
        if not node:
            return None

        user = info.context.user
        if node.user == user or user_has_view_permission(
            user, CustomerProfile, BerthApplication, BerthLease
        ):
            return node
        else:
            raise VenepaikkaGraphQLError(
                _("You do not have permission to perform this action.")
            )
