import django_filters
import graphene
from graphene import relay
from graphene_django import DjangoConnectionField, DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphene_federation import extend, external
from graphql_jwt.decorators import login_required

from applications.models import BerthApplication
from applications.new_schema import BerthApplicationNode, WinterStorageApplicationNode
from applications.new_schema.types import WinterStorageApplicationFilter
from leases.models import BerthLease
from leases.schema import BerthLeaseNode, WinterStorageLeaseNode
from utils.relay import get_node_from_global_id, return_node_if_user_has_permissions
from utils.schema import CountConnection

from ..enums import BoatCertificateType, InvoicingType, OrganizationType
from ..models import Boat, BoatCertificate, CustomerProfile, Organization

InvoicingTypeEnum = graphene.Enum.from_enum(InvoicingType)
OrganizationTypeEnum = graphene.Enum.from_enum(OrganizationType)
BoatCertificateTypeEnum = graphene.Enum.from_enum(BoatCertificateType)

CustomerGroupEnum = graphene.Enum(
    "CustomerGroup",
    [("PRIVATE", "private")] + [(enum.name, enum.value) for enum in OrganizationType],
)


class BoatCertificateNode(DjangoObjectType):
    certificate_type = BoatCertificateTypeEnum(required=True)

    class Meta:
        model = BoatCertificate
        interfaces = (relay.Node,)
        connection_class = CountConnection
        exclude = ("boat",)

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


class BerthApplicationFilter(django_filters.FilterSet):
    order_by = django_filters.OrderingFilter(
        fields=(("created_at", "createdAt"),),
        label="Supports `createdAt` and `-createdAt`.",
    )


class ProfileFilterSet(django_filters.FilterSet):
    class Meta:
        model = CustomerProfile
        fields = ("comment",)

    comment = django_filters.CharFilter(lookup_expr="icontains")


@extend(fields="id")
class ProfileNode(DjangoObjectType):
    """
    ProfileNode extended from the open-city-profile's ProfileNode.
    """

    class Meta:
        model = CustomerProfile
        fields = (
            "id",
            "invoicing_type",
            "comment",
            "organization",
            "boats",
            "berth_applications",
            "berth_leases",
            "winter_storage_applications",
            "winter_storage_leases",
            "orders",
        )
        interfaces = (relay.Node,)
        connection_class = CountConnection

    # explicitly mark shadowed ID field as external
    # otherwise, graphene-federation cannot catch it.
    # TODO: maybe later investigate other approaches for this?
    #  This one might or might not be the right one.
    id = external(relay.GlobalID())

    # The fields below come from our backend.
    # BEWARE: since ProfileNode is extended, none of its
    # fields could be non-nullable (i.e. required=True),
    # because then the entire ProfileNode will be null at
    # the federation level, if the profile object has no
    # object in our database.
    invoicing_type = InvoicingTypeEnum()
    comment = graphene.String()
    customer_group = CustomerGroupEnum()
    organization = graphene.Field(OrganizationNode)
    boats = DjangoConnectionField(BoatNode)
    berth_applications = DjangoFilterConnectionField(
        BerthApplicationNode,
        filterset_class=BerthApplicationFilter,
        description="`BerthApplications` are ordered by `createdAt` in ascending order by default.",
    )
    berth_leases = DjangoConnectionField(BerthLeaseNode)
    winter_storage_applications = DjangoFilterConnectionField(
        WinterStorageApplicationNode,
        filterset_class=WinterStorageApplicationFilter,
        description="`WinterStorageApplications` are ordered by `createdAt` in ascending order by default.",
    )
    winter_storage_leases = DjangoConnectionField(WinterStorageLeaseNode)
    orders = DjangoConnectionField("payments.schema.OrderNode")

    def resolve_berth_applications(self, info, **kwargs):
        return self.berth_applications.order_by("created_at")

    def resolve_winter_storage_applications(self, info, **kwargs):
        return self.winter_storage_applications.order_by("created_at")

    @login_required
    def __resolve_reference(self, info, **kwargs):
        profile = get_node_from_global_id(info, self.id, only_type=ProfileNode)
        return return_node_if_user_has_permissions(
            profile, info.context.user, CustomerProfile, BerthApplication, BerthLease
        )

    @classmethod
    @login_required
    def get_node(cls, info, id):
        node = super().get_node(info, id)
        return return_node_if_user_has_permissions(
            node, info.context.user, CustomerProfile, BerthApplication, BerthLease
        )
