import graphene
from graphene import relay
from graphene_django import DjangoObjectType

from ..enums import ContractStatus
from ..models import VismaBerthContract, VismaWinterStorageContract

ContractStatusEnum = graphene.Enum.from_enum(ContractStatus)


class BerthContractNode(DjangoObjectType):
    class Meta:
        model = VismaBerthContract
        interfaces = (relay.Node,)
        exclude_fields = ("document_id", "invitation_id", "passphrase")

    status = ContractStatusEnum()

    @classmethod
    def get_queryset(cls, queryset, info):
        return super().get_queryset(queryset, info)


class WinterStorageContractNode(DjangoObjectType):
    class Meta:
        model = VismaWinterStorageContract
        interfaces = (relay.Node,)
        exclude_fields = ("document_id", "invitation_id", "passphrase")

    status = ContractStatusEnum()

    @classmethod
    def get_queryset(cls, queryset, info):
        return super().get_queryset(queryset, info)


class AuthMethod(graphene.ObjectType):
    identifier = graphene.NonNull(graphene.String)
    name = graphene.NonNull(graphene.String)
    image = graphene.NonNull(graphene.String)


class ContractSignedType(graphene.ObjectType):
    is_signed = graphene.Boolean()
