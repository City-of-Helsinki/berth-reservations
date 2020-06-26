import graphene
from django.core.exceptions import ValidationError
from django.db import transaction
from graphene_file_upload.scalars import Upload

from berth_reservations.exceptions import VenepaikkaGraphQLError
from users.decorators import (
    add_permission_required,
    change_permission_required,
    delete_permission_required,
)
from utils.relay import get_node_from_global_id
from utils.schema import update_object

from ..models import BoatCertificate
from .types import BoatCertificateNode, BoatCertificateTypeEnum, BoatNode


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
