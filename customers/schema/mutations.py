import graphene
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils.translation import gettext_lazy as _
from graphene_file_upload.scalars import Upload
from graphql_jwt.decorators import login_required

from berth_reservations.exceptions import VenepaikkaGraphQLError
from resources.models import BoatType
from users.decorators import (
    add_permission_required,
    change_permission_required,
    delete_permission_required,
)
from utils.relay import from_global_id, get_node_from_global_id
from utils.schema import update_object

from ..models import Boat, BoatCertificate, CustomerProfile, Organization
from ..services import ProfileService
from .types import (
    BoatCertificateNode,
    BoatCertificateTypeEnum,
    BoatNode,
    InvoicingTypeEnum,
    OrganizationTypeEnum,
    ProfileNode,
)


def add_boat_certificates(certificates, boat):
    try:
        for cert_input in certificates:
            BoatCertificate.objects.create(**cert_input, boat=boat)
    except IntegrityError as e:
        raise VenepaikkaGraphQLError(e)


def update_boat_certificates(certificates, info):
    try:
        for cert_input in certificates:
            cert = get_node_from_global_id(
                info,
                cert_input.pop("id"),
                only_type=BoatCertificateNode,
                nullable=False,
            )
            update_object(cert, cert_input)
    except IntegrityError as e:
        raise VenepaikkaGraphQLError(e)


def remove_boat_certificates(certificates, boat):
    try:
        for cert_id in certificates:
            cert_id = from_global_id(cert_id)
            BoatCertificate.objects.get(pk=cert_id, boat=boat).delete()
    except BoatCertificate.DoesNotExist as e:
        raise VenepaikkaGraphQLError(e)


class BoatCertificateInput(graphene.InputObjectType):
    file = Upload()
    certificate_type = BoatCertificateTypeEnum()
    valid_until = graphene.Date()
    checked_at = graphene.Date()
    checked_by = graphene.String()


class AddBoatCertificateInput(BoatCertificateInput):
    certificate_type = BoatCertificateTypeEnum(required=True)


class UpdateBoatCertificateInput(BoatCertificateInput):
    id = graphene.ID(required=True)


class BoatInput:
    boat_type_id = graphene.ID()
    registration_number = graphene.String()
    name = graphene.String()
    model = graphene.String()
    length = graphene.Decimal()
    width = graphene.Decimal()
    draught = graphene.Decimal()
    weight = graphene.Int()
    propulsion = graphene.String()
    hull_material = graphene.String()
    intended_use = graphene.String()
    add_boat_certificates = graphene.List(AddBoatCertificateInput)


class CreateBoatMutation(graphene.ClientIDMutation):
    class Input(BoatInput):
        owner_id = graphene.ID(required=True)
        boat_type_id = graphene.ID(required=True)
        length = graphene.Decimal(required=True)
        width = graphene.Decimal(required=True)

    boat = graphene.Field(BoatNode)

    @classmethod
    @add_permission_required(Boat, BoatCertificate)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        owner = get_node_from_global_id(
            info, input.pop("owner_id"), only_type=ProfileNode, nullable=False
        )
        input["owner"] = owner
        try:
            input["boat_type"] = BoatType.objects.get(id=input.pop("boat_type_id"))
        except BoatType.DoesNotExist as e:
            raise VenepaikkaGraphQLError(e)

        add_certificates = input.pop("add_boat_certificates", [])

        try:
            boat = Boat.objects.create(**input)
            add_boat_certificates(add_certificates, boat)
        except ValidationError as e:
            # Flatten all the error messages on a single list
            errors = sum(e.message_dict.values(), [])
            raise VenepaikkaGraphQLError(errors)

        return CreateBoatMutation(boat=boat)


class UpdateBoatMutation(graphene.ClientIDMutation):
    class Input(BoatInput):
        id = graphene.ID(required=True)
        update_boat_certificates = graphene.List(UpdateBoatCertificateInput)
        remove_boat_certificates = graphene.List(graphene.ID)

    boat = graphene.Field(BoatNode)

    @classmethod
    @add_permission_required(BoatCertificate)
    @change_permission_required(Boat)
    @delete_permission_required(BoatCertificate)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        boat = get_node_from_global_id(
            info, input.pop("id"), only_type=BoatNode, nullable=False
        )

        add_certificates = input.pop("add_boat_certificates", [])
        update_certificates = input.pop("update_boat_certificates", [])
        remove_certificates = input.pop("remove_boat_certificates", [])

        try:
            update_object(boat, input)
            remove_boat_certificates(remove_certificates, boat)
            update_boat_certificates(update_certificates, info)
            add_boat_certificates(add_certificates, boat)
        except ValidationError as e:
            raise VenepaikkaGraphQLError(e)

        return UpdateBoatMutation(boat=boat)


class DeleteBoatMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(Boat)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        boat = get_node_from_global_id(
            info, input.pop("id"), only_type=BoatNode, nullable=False
        )

        boat.delete()

        return DeleteBoatMutation()


class OrganizationInput(graphene.InputObjectType):
    organization_type = OrganizationTypeEnum(required=True)
    business_id = graphene.String()
    name = graphene.String()
    address = graphene.String()
    postal_code = graphene.String()
    city = graphene.String()


class BerthServicesInput:
    invoicing_type = InvoicingTypeEnum()
    comment = graphene.String()


class CreateBerthServicesProfileMutation(graphene.ClientIDMutation):
    class Input(BerthServicesInput):
        id = graphene.GlobalID(
            required=True,
            description="`GlobalID` associated to the Open City Profile customer profile",
        )
        organization = OrganizationInput()

    profile = graphene.Field(ProfileNode)

    @classmethod
    @add_permission_required(CustomerProfile, Organization)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        input["id"] = from_global_id(global_id=input.pop("id"), node_type=ProfileNode)

        organization_input = None
        if "organization" in input:
            organization_input = input.pop("organization")

        try:
            profile = CustomerProfile.objects.create(**input)
            if organization_input:
                Organization.objects.create(customer=profile, **organization_input)
        except ValidationError as e:
            # Flatten all the error messages on a single list
            errors = sum(e.message_dict.values(), [])
            raise VenepaikkaGraphQLError(errors)

        return CreateBerthServicesProfileMutation(profile=profile)


class CreateMyBerthProfileMutation(graphene.ClientIDMutation):
    class Input:
        profile_token = graphene.String(
            required=True, description="API token for Helsinki profile GraphQL API",
        )

    profile = graphene.Field(ProfileNode)

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, profile_token, **input):
        user = info.context.user
        profile_exists = CustomerProfile.objects.filter(user=user).exists()
        if profile_exists:
            return None

        profile_service = ProfileService(profile_token=profile_token)
        my_profile = profile_service.get_my_profile()
        if not my_profile:
            raise VenepaikkaGraphQLError("Open city profile not found")

        try:
            profile = CustomerProfile.objects.create(id=my_profile.id, user=user)
        except ValidationError as e:
            # Flatten all the error messages on a single list
            errors = sum(e.message_dict.values(), [])
            raise VenepaikkaGraphQLError(errors)

        return CreateMyBerthProfileMutation(profile=profile)


class UpdateBerthServicesProfileMutation(graphene.ClientIDMutation):
    class Input(BerthServicesInput):
        id = graphene.GlobalID(required=True)
        organization = OrganizationInput(
            description="With the values provided, the Organization associated to the Profile "
            "will be either created or updated as required."
        )
        delete_organization = graphene.Boolean(
            description="If `true` is passed, the organization will be deleted."
        )

    profile = graphene.Field(ProfileNode)

    @classmethod
    @add_permission_required(Organization)
    @change_permission_required(CustomerProfile, Organization)
    @delete_permission_required(Organization)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        profile = get_node_from_global_id(
            info, input.pop("id"), only_type=ProfileNode, nullable=False
        )

        delete_organization = input.pop("delete_organization", False)
        if delete_organization:
            if "organization" in input:
                raise VenepaikkaGraphQLError(
                    _("You cannot pass deleteOrganization: true and organization input")
                )
            if not profile.organization:
                raise VenepaikkaGraphQLError(
                    _("The passed Profile is not associated with an Organization")
                )
            profile.organization.delete()
            profile.refresh_from_db()
        elif "organization" in input:
            Organization.objects.update_or_create(
                customer=profile, defaults=input.pop("organization")
            )
            profile.refresh_from_db()

        try:
            update_object(profile, input)
        except ValidationError as e:
            # Flatten all the error messages on a single list
            errors = sum(e.message_dict.values(), [])
            raise VenepaikkaGraphQLError(errors)

        return UpdateBerthServicesProfileMutation(profile=profile)


class DeleteBerthServicesProfileMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(CustomerProfile, Organization)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        profile = get_node_from_global_id(
            info, input.pop("id"), only_type=ProfileNode, nullable=False
        )

        profile.delete()

        return DeleteBoatMutation()


class Mutation:
    create_boat = CreateBoatMutation.Field(
        description="Creates a `Boat` associated with the `ProfileNode` passed."
        "\n\n**Requires permissions** to create boats."
        "\n\nErrors:"
        "\n* The passed customer doesn't exist"
        "\n* The passed boat type doesn't exist"
    )
    update_boat = UpdateBoatMutation.Field(
        description="Updates a `Boat`."
        "\n\n**Requires permissions** to update boats."
        "\n\nErrors:"
        "\n* The passed boat doesn't exist"
        "\n* The passed boat type doesn't exist"
        "\n* The passed `removeBoatCertificates` don't exist"
    )
    delete_boat = DeleteBoatMutation.Field(
        description="Deletes a `Boat` object."
        "\n\n**Requires permissions** to delete boats."
        "\n\nErrors:"
        "\n* The passed boat doesn't exist"
    )

    create_berth_services_profile = CreateBerthServicesProfileMutation.Field(
        description="Creates a `ProfileNode`."
        "\n\n**Requires permissions** to create profiles."
        "\n\nA customer GlobalID is required from an existing user from Open City Profile. "
        "The created `BerthServicesProfile` will be associated to that Open City profile."
        "\n\nErrors:"
        "\n* No customer `GlobalID` is provided"
    )
    create_my_berth_profile = CreateMyBerthProfileMutation.Field(
        description="Creates a `ProfileNode` for the current user."
        "\n\nA customer profile_token is required from the current user."
        "\n\nThe `Profile` UUID is fetched for the current user from Open City profile "
        "and a `CustomerProfile` is created with the same UUID."
        "\nThe created `CustomerProfile` will thus be associated to that Open City profile."
        "\n\nErrors:"
        "\n* Open city profile not found"
    )
    update_berth_services_profile = UpdateBerthServicesProfileMutation.Field(
        description="Updates a `ProfileNode`."
        "\n\n**Requires permissions** to update profiles."
        "\n\nIf an `organization` field is passed on the input, it will create or update "
        "the Organization associated to this profile."
        "\n\nErrors:"
        "\n* No customer `GlobalID` is provided"
        "\n* Both `organization` and `deleteOrganization: true` are passed"
    )
    delete_berth_services_profile = DeleteBerthServicesProfileMutation.Field(
        description="Deletes a `ProfileNode` object."
        "\n\n**Requires permissions** to delete profiles."
        "\n\nErrors:"
        "\n* The passed profile doesn't exist"
    )
