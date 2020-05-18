import graphene
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from berth_reservations.exceptions import VenepaikkaGraphQLError
from resources.schema import HarborNode
from users.decorators import (
    add_permission_required,
    change_permission_required,
    delete_permission_required,
)
from utils.relay import get_node_from_global_id
from utils.schema import update_object

from ..models import BerthProduct
from .types import BerthPriceGroupNode, BerthProductNode


class CreateBerthProductMutation(graphene.ClientIDMutation):
    class Input:
        price_value = graphene.Decimal(required=True)
        price_group_id = graphene.ID(required=True)
        harbor_id = graphene.ID()

    berth_product = graphene.Field(BerthProductNode)

    @classmethod
    @add_permission_required(BerthProduct)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        input["harbor"] = get_node_from_global_id(
            info, input.pop("harbor_id", None), only_type=HarborNode, nullable=True,
        )
        input["price_group"] = get_node_from_global_id(
            info,
            input.pop("price_group_id", None),
            only_type=BerthPriceGroupNode,
            nullable=False,
        )
        try:
            product = BerthProduct.objects.create(**input)
        except (ValidationError, IntegrityError) as e:
            raise VenepaikkaGraphQLError(e)

        return CreateBerthProductMutation(berth_product=product)


class UpdateBerthProductMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        price_value = graphene.Decimal()
        price_group_id = graphene.ID()
        harbor_id = graphene.ID()

    berth_product = graphene.Field(BerthProductNode)

    @classmethod
    @change_permission_required(BerthProduct)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        product = get_node_from_global_id(
            info, input.pop("id"), only_type=BerthProductNode, nullable=False
        )
        if "harbor_id" in input:
            input["harbor"] = get_node_from_global_id(
                info, input.pop("harbor_id", None), only_type=HarborNode, nullable=True,
            )
        if "price_group_id" in input:
            input["price_group"] = get_node_from_global_id(
                info,
                input.pop("price_group_id", None),
                only_type=BerthPriceGroupNode,
                nullable=False,
            )
        try:
            update_object(product, input)
        except (ValidationError, IntegrityError) as e:
            raise VenepaikkaGraphQLError(e)

        return UpdateBerthProductMutation(berth_product=product)


class DeleteBerthProductMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(BerthProduct)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        product = get_node_from_global_id(
            info, input.pop("id"), only_type=BerthProductNode, nullable=False,
        )

        product.delete()

        return DeleteBerthProductMutation()


class Mutation:
    create_berth_product = CreateBerthProductMutation.Field(
        description="Creates a `BerthProduct` object."
        "\n\n**Requires permissions** to edit payments."
        "\n\nErrors:"
        "\n* A `BerthPriceGroup` is not passed"
    )
    update_berth_product = UpdateBerthProductMutation.Field(
        description="Updates a `BerthProduct` object."
        "\n\n**Requires permissions** to edit payments."
        "\n\nErrors:"
        "\n* The `BerthProduct` doesn't exist"
    )
    delete_berth_product = DeleteBerthProductMutation.Field(
        description="Deletes a `BerthProduct` object."
        "\n\n**Requires permissions** to edit payments."
        "\n\nErrors:"
        "\n* The `BerthProduct` doesn't exist"
    )
