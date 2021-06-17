import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphql_jwt.decorators import login_required

from utils.relay import return_queryset_if_user_has_permissions

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
    @login_required
    def get_queryset(cls, queryset, info):
        user = info.context.user
        return return_queryset_if_user_has_permissions(
            queryset, user, VismaBerthContract,
        )


class WinterStorageContractNode(DjangoObjectType):
    class Meta:
        model = VismaWinterStorageContract
        interfaces = (relay.Node,)
        exclude_fields = ("document_id", "invitation_id", "passphrase")

    status = ContractStatusEnum()

    @classmethod
    @login_required
    def get_queryset(cls, queryset, info):
        user = info.context.user
        return return_queryset_if_user_has_permissions(
            queryset, user, VismaWinterStorageContract,
        )


class AuthMethod(graphene.ObjectType):
    identifier = graphene.NonNull(graphene.String)
    name = graphene.NonNull(graphene.String)
    image = graphene.NonNull(graphene.String)


class ContractSignedType(graphene.ObjectType):
    is_signed = graphene.Boolean()
