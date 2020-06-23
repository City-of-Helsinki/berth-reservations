import django_filters
import graphene
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import ugettext_lazy as _
from graphene import relay
from graphene_django import DjangoConnectionField
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType
from graphene_federation import extend, external
from graphene_file_upload.scalars import Upload
from graphql_jwt.decorators import login_required

from applications.models import BerthApplication
from applications.new_schema import BerthApplicationNode
from berth_reservations.exceptions import VenepaikkaGraphQLError
from leases.models import BerthLease
from leases.schema import BerthLeaseNode
from resources.schema import update_object
from users.decorators import (
    add_permission_required,
    change_permission_required,
    delete_permission_required,
    view_permission_required,
)
from users.utils import user_has_view_permission
from utils.enum import graphene_enum
from utils.relay import get_node_from_global_id
from utils.schema import CountConnection

from .enums import BoatCertificateType, InvoicingType, OrganizationType
from .models import Boat, BoatCertificate, CustomerProfile, Organization

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
        fields = (
            "business_id",
            "name",
            "address",
            "postal_code",
            "city",
        )
        connection_class = CountConnection


PROFILE_NODE_FIELDS = (
    "id",
    "invoicing_type",
    "comment",
    "organization",
    "boats",
    "berth_applications",
    "berth_leases",
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


class BoatCertificateInput:
    file = Upload()
    certificate_type = BoatCertificateTypeEnum()
    valid_until = graphene.Date()
    checked_at = graphene.Date()
    checked_by = graphene.String()


class CreateBoatCertificateMutation(graphene.ClientIDMutation):
    class Input(BoatCertificateInput):
        boat_id = graphene.ID(required=True)
        certificate_type = BoatCertificateTypeEnum(required=True)

    boat_certificate = graphene.Field(BoatCertificateNode)

    @classmethod
    @add_permission_required(BoatCertificate)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        boat = get_node_from_global_id(
            info, input.pop("boat_id"), only_type=BoatNode, nullable=False
        )
        input["boat"] = boat

        try:
            certificate = BoatCertificate.objects.create(**input)
        except ValidationError as e:
            # Flatten all the error messages on a single list
            errors = sum(e.message_dict.values(), [])
            raise VenepaikkaGraphQLError(errors)

        return CreateBoatCertificateMutation(boat_certificate=certificate)


class UpdateBoatCertificateMutation(graphene.ClientIDMutation):
    class Input(BoatCertificateInput):
        id = graphene.ID(required=True)

    boat_certificate = graphene.Field(BoatCertificateNode)

    @classmethod
    @change_permission_required(BoatCertificate)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        certificate = get_node_from_global_id(
            info, input.pop("id"), only_type=BoatCertificateNode, nullable=False
        )

        try:
            update_object(certificate, input)
        except ValidationError as e:
            # Flatten all the error messages on a single list
            errors = sum(e.message_dict.values(), [])
            raise VenepaikkaGraphQLError(errors)

        return UpdateBoatCertificateMutation(boat_certificate=certificate)


class DeleteBoatCertificateMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(BoatCertificate)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        certificate = get_node_from_global_id(
            info, input.pop("id"), only_type=BoatCertificateNode, nullable=False
        )

        certificate.delete()

        return DeleteBoatCertificateMutation()


class Mutation:
    create_boat_certificate = CreateBoatCertificateMutation.Field(
        description="Creates a `BoatCertificate` associated with `Boat` passed. "
        "A `Boat` can only have one certificate from each `BoatCertificateType`."
        "\n\n**Requires permissions** to create boat certificates."
    )
    update_boat_certificate = UpdateBoatCertificateMutation.Field(
        description="Updates a `BoatCertificate` object."
        "\n\n**Requires permissions** to edit boat certificates."
        "\n\nErrors:"
        "\n* The passed certificate ID doesn't exist"
    )
    delete_boat_certificate = DeleteBoatCertificateMutation.Field(
        description="Deletes a `BoatCertificate` object."
        "\n\nErrors:"
        "\n* The passed certificate ID doesn't exist"
    )


class Query:
    berth_profile = graphene.relay.Node.Field(BerthProfileNode)
    berth_profiles = DjangoFilterConnectionField(BerthProfileNode)

    @view_permission_required(CustomerProfile, BerthApplication, BerthLease)
    def resolve_berth_profiles(self, info, **kwargs):
        return CustomerProfile.objects.all()
