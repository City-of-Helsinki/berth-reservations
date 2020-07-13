import graphene
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from graphene_file_upload.scalars import Upload

from berth_reservations.exceptions import VenepaikkaGraphQLError
from resources.models import BoatType
from users.decorators import (
    add_permission_required,
    change_permission_required,
    delete_permission_required,
)
from utils.relay import from_global_id, get_node_from_global_id
from utils.schema import update_object

from ..models import Boat, BoatCertificate
from .types import BoatCertificateNode, BoatCertificateTypeEnum, BoatNode, ProfileNode


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
        "\n\nErrors:"
        "\n* The passed boat doesn't exist"
    )
