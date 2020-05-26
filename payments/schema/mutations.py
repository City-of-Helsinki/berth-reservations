import graphene
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from berth_reservations.exceptions import VenepaikkaGraphQLError
from resources.schema import HarborNode, WinterStorageAreaNode
from users.decorators import (
    add_permission_required,
    change_permission_required,
    delete_permission_required,
)
from utils.relay import get_node_from_global_id
from utils.schema import update_object

from ..models import AdditionalProduct, BerthProduct, WinterStorageProduct
from .types import (
    AdditionalProductNode,
    AdditionalProductTaxEnum,
    BerthPriceGroupNode,
    BerthProductNode,
    PeriodTypeEnum,
    PriceUnitsEnum,
    ServiceTypeEnum,
    WinterStorageProductNode,
)


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


class CreateWinterStorageProductMutation(graphene.ClientIDMutation):
    class Input:
        price_value = graphene.Decimal(required=True)
        winter_storage_area_id = graphene.ID()

    winter_storage_product = graphene.Field(WinterStorageProductNode)

    @classmethod
    @add_permission_required(WinterStorageProduct)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        input["winter_storage_area"] = get_node_from_global_id(
            info,
            input.pop("winter_storage_area_id", None),
            only_type=WinterStorageAreaNode,
            nullable=True,
        )
        try:
            product = WinterStorageProduct.objects.create(**input)
        except (ValidationError, IntegrityError) as e:
            raise VenepaikkaGraphQLError(e)
        return CreateWinterStorageProductMutation(winter_storage_product=product)


class UpdateWinterStorageProductMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        price_value = graphene.Decimal()
        winter_storage_area_id = graphene.ID()

    winter_storage_product = graphene.Field(WinterStorageProductNode)

    @classmethod
    @change_permission_required(WinterStorageProduct)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        product = get_node_from_global_id(
            info, input.pop("id"), only_type=WinterStorageProductNode, nullable=False
        )
        if "winter_storage_area_id" in input:
            input["winter_storage_area"] = get_node_from_global_id(
                info,
                input.pop("winter_storage_area_id", None),
                only_type=WinterStorageAreaNode,
                nullable=True,
            )
        try:
            update_object(product, input)
        except (ValidationError, IntegrityError) as e:
            raise VenepaikkaGraphQLError(e)

        return UpdateWinterStorageProductMutation(winter_storage_product=product)


class DeleteWinterStorageProductMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(WinterStorageProduct)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        product = get_node_from_global_id(
            info, input.pop("id"), only_type=WinterStorageProductNode, nullable=False,
        )

        product.delete()

        return DeleteWinterStorageProductMutation()


class AdditionalProductInput:
    service = ServiceTypeEnum()
    period = PeriodTypeEnum()
    price_value = graphene.Decimal()
    price_unit = PriceUnitsEnum()
    tax_percentage = AdditionalProductTaxEnum()


class CreateAdditionalProductMutation(graphene.ClientIDMutation):
    class Input(AdditionalProductInput):
        service = ServiceTypeEnum(required=True)
        period = PeriodTypeEnum(required=True)
        price_value = graphene.Decimal(required=True)

    additional_product = graphene.Field(AdditionalProductNode)

    @classmethod
    @add_permission_required(AdditionalProduct)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        try:
            product = AdditionalProduct.objects.create(**input)
        except (ValidationError, IntegrityError) as e:
            raise VenepaikkaGraphQLError(e)
        return CreateAdditionalProductMutation(additional_product=product)


class UpdateAdditionalProductMutation(graphene.ClientIDMutation):
    class Input(AdditionalProductInput):
        id = graphene.ID(required=True)

    additional_product = graphene.Field(AdditionalProductNode)

    @classmethod
    @add_permission_required(AdditionalProduct)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        product = get_node_from_global_id(
            info, input.pop("id"), only_type=AdditionalProductNode, nullable=False
        )
        try:
            update_object(product, input)
        except (ValidationError, IntegrityError) as e:
            raise VenepaikkaGraphQLError(e)
        return UpdateAdditionalProductMutation(additional_product=product)


class DeleteAdditionalProductMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(AdditionalProduct)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        product = get_node_from_global_id(
            info, input.pop("id"), only_type=AdditionalProductNode, nullable=False,
        )

        product.delete()

        return DeleteAdditionalProductMutation()


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

    create_winter_storage_product = CreateWinterStorageProductMutation.Field(
        description="Creates a `WinterStorageProduct` object."
        "\n\n**Requires permissions** to edit payments."
    )
    update_winter_storage_product = UpdateWinterStorageProductMutation.Field(
        description="Updates a `WinterStorageProduct` object."
        "\n\n**Requires permissions** to edit payments."
        "\n\nErrors:"
        "\n* The `WinterStorageProduct` doesn't exist"
    )
    delete_winter_storage_product = DeleteWinterStorageProductMutation.Field(
        description="Deletes a `WinterStorageProduct` object."
        "\n\n**Requires permissions** to edit payments."
        "\n\nErrors:"
        "\n* The `WinterStorageProduct` doesn't exist"
    )

    create_additional_product = CreateAdditionalProductMutation.Field(
        description="Deletes a `AdditionalProduct` object."
        "\n\n**Requires permissions** to edit payments."
    )
    update_additional_product = UpdateAdditionalProductMutation.Field(
        description="Updates a `AdditionalProduct` object."
        "\n\n**Requires permissions** to edit payments."
        "\n\nErrors:"
        "\n* The `AdditionalProduct` doesn't exist"
    )
    delete_additional_product = DeleteAdditionalProductMutation.Field(
        description="Deletes a `AdditionalProduct` object."
        "\n\n**Requires permissions** to edit payments."
        "\n\nErrors:"
        "\n* The `AdditionalProduct` doesn't exist"
    )
