import graphene
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils.translation import ugettext_lazy as _

from berth_reservations.exceptions import VenepaikkaGraphQLError
from customers.schema import ProfileNode
from leases.models import BerthLease, WinterStorageLease
from leases.schema import BerthLeaseNode, WinterStorageLeaseNode
from resources.schema import HarborNode, WinterStorageAreaNode
from users.decorators import (
    add_permission_required,
    change_permission_required,
    delete_permission_required,
    view_permission_required,
)
from utils.relay import get_node_from_global_id
from utils.schema import update_object

from ..models import (
    AdditionalProduct,
    BerthProduct,
    Order,
    OrderLine,
    WinterStorageProduct,
)
from .types import (
    AdditionalProductNode,
    AdditionalProductTaxEnum,
    BerthPriceGroupNode,
    BerthProductNode,
    OrderLineNode,
    OrderNode,
    OrderStatusEnum,
    PeriodTypeEnum,
    PriceUnitsEnum,
    ProductServiceTypeEnum,
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
    service = ProductServiceTypeEnum()
    period = PeriodTypeEnum()
    price_value = graphene.Decimal()
    price_unit = PriceUnitsEnum()
    tax_percentage = AdditionalProductTaxEnum()


class CreateAdditionalProductMutation(graphene.ClientIDMutation):
    class Input(AdditionalProductInput):
        service = ProductServiceTypeEnum(required=True)
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
    @change_permission_required(AdditionalProduct)
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


class OrderInput:
    lease_id = graphene.ID()
    status = OrderStatusEnum()
    comment = graphene.String()
    due_date = graphene.Date()


class CreateOrderMutation(graphene.ClientIDMutation):
    class Input(OrderInput):
        customer_id = graphene.ID(required=True)
        product_id = graphene.ID()

    order = graphene.Field(OrderNode)

    @classmethod
    @add_permission_required(Order)
    @view_permission_required(BerthLease, WinterStorageLease)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        input["customer"] = get_node_from_global_id(
            info, input.pop("customer_id"), ProfileNode, nullable=False
        )
        product_id = input.pop("product_id", None)
        if product_id:
            product = None
            try:
                product = get_node_from_global_id(
                    info, product_id, BerthProductNode, nullable=True
                )
            # If a different node type is received get_node raises an assertion error
            # when trying to validate the type
            except AssertionError:
                product = get_node_from_global_id(
                    info, product_id, WinterStorageProductNode, nullable=True
                )
            finally:
                if product:
                    input["product"] = product

        lease_id = input.pop("lease_id", None)
        if lease_id:
            lease = None
            try:
                lease = get_node_from_global_id(
                    info, lease_id, BerthLeaseNode, nullable=True
                )
            # If a different node type is received get_node raises an assertion error
            # when trying to validate the type
            except AssertionError:
                lease = get_node_from_global_id(
                    info, lease_id, WinterStorageLeaseNode, nullable=True
                )
            finally:
                if not lease:
                    raise VenepaikkaGraphQLError(
                        _("Lease with the given ID does not exist")
                    )
                input["lease"] = lease

        try:
            order = Order.objects.create(**input)
        except (ValidationError, IntegrityError) as e:
            raise VenepaikkaGraphQLError(e)
        return CreateOrderMutation(order=order)


class UpdateOrderMutation(graphene.ClientIDMutation):
    class Input(OrderInput):
        id = graphene.ID(required=True)

    order = graphene.Field(OrderNode)

    @classmethod
    @change_permission_required(Order)
    @view_permission_required(BerthLease, WinterStorageLease)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        order = get_node_from_global_id(
            info, input.pop("id"), only_type=OrderNode, nullable=False
        )
        lease_id = input.pop("lease_id", None)
        if lease_id:
            lease = None
            try:
                lease = get_node_from_global_id(
                    info, lease_id, BerthLeaseNode, nullable=True
                )
            # If a different node type is received get_node raises an assertion error
            # when trying to validate the type
            except AssertionError:
                lease = get_node_from_global_id(
                    info, lease_id, WinterStorageLeaseNode, nullable=True
                )
            finally:
                if not lease:
                    raise VenepaikkaGraphQLError(
                        _("Lease with the given ID does not exist")
                    )
                input["lease"] = lease

        try:
            update_object(order, input)
        except (ValidationError, IntegrityError) as e:
            raise VenepaikkaGraphQLError(e)
        return UpdateOrderMutation(order=order)


class DeleteOrderMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(BerthProduct)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        order = get_node_from_global_id(
            info, input.pop("id"), only_type=OrderNode, nullable=False,
        )

        order.delete()

        return DeleteBerthProductMutation()


class OrderLineInput:
    quantity = graphene.Int(description="Defaults to 1")


class CreateOrderLineMutation(graphene.ClientIDMutation):
    class Input(OrderLineInput):
        order_id = graphene.ID(required=True)
        product_id = graphene.ID(required=True)

    order_line = graphene.Field(OrderLineNode)
    order = graphene.Field(OrderNode)

    @classmethod
    @add_permission_required(OrderLine)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        input["order"] = get_node_from_global_id(
            info, input.pop("order_id"), only_type=OrderNode, nullable=False
        )
        input["product"] = get_node_from_global_id(
            info,
            input.pop("product_id"),
            only_type=AdditionalProductNode,
            nullable=False,
        )

        try:
            order_line = OrderLine.objects.create(**input)
        except (ValidationError, IntegrityError) as e:
            raise VenepaikkaGraphQLError(e)
        return CreateOrderLineMutation(order_line=order_line, order=order_line.order)


class UpdateOrderLineMutation(graphene.ClientIDMutation):
    class Input(OrderLineInput):
        id = graphene.ID(required=True)

    order_line = graphene.Field(OrderLineNode)
    order = graphene.Field(OrderNode)

    @classmethod
    @change_permission_required(OrderLine)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        order_line = get_node_from_global_id(
            info, input.pop("id"), only_type=OrderLineNode, nullable=False
        )

        try:
            update_object(order_line, input)
        except (ValidationError, IntegrityError) as e:
            raise VenepaikkaGraphQLError(e)
        return UpdateOrderLineMutation(order_line=order_line, order=order_line.order)


class DeleteOrderLineMutation(graphene.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @delete_permission_required(OrderLine)
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        order_line = get_node_from_global_id(
            info, input.pop("id"), only_type=OrderLineNode, nullable=False
        )

        order_line.delete()

        return DeleteOrderLineMutation()


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

    create_order = CreateOrderMutation.Field(
        description="Creates an `Order` object and the `OrderLine`s according to the place associated."
        "\n\n**Requires permissions** to edit payments."
        "\n\nErrors:"
        "\n* The `customer` does not exist"
        "\n* A `BerthProduct` and a `WinterStorageLease` are passed"
        "\n* A `WinterStorageProduct` and a `BerthLease` are passed"
        "\n* The `lease` provided belongs to a different `customer`"
        "\n* An invalid `product` (neither `BerthProduct` nor `WinterStorageProduct`) is passed"
    )
    update_order = UpdateOrderMutation.Field(
        description="Updates an `Order` object."
        "\n\n**Requires permissions** to edit payments."
        "\n\nErrors:"
        "\n* The passed `order` does not exist"
        "\n* A different `product` is trying to be assigned"
        "\n* A different `lease` is trying to be assigned"
    )
    delete_order = DeleteOrderMutation.Field(
        description="Deletes an `Order` object."
        "\n\n**Requires permissions** to edit payments."
        "\n\nErrors:"
        "\n* The passed `order` does not exist"
    )

    create_order_line = CreateOrderLineMutation.Field(
        description="Creates an `OrderLine` object."
        "\n\n**Requires permissions** to edit payments."
        "\n\nErrors:"
        "\n* The passed `order` doesn't exist"
        "\n* The passed `product` doesn't exist"
    )
    update_order_line = UpdateOrderLineMutation.Field(
        description="Updates an `OrderLine` object."
        "\n\n**Requires permissions** to edit payments."
        "\n\nErrors:"
        "\n* The passed `OrderLine` does not exist"
        "\n* A different `order` is trying to be assigned"
        "\n* A different `product` is trying to be assigned"
    )
    delete_order_line = DeleteOrderLineMutation.Field(
        description="Deletes an `OrderLine` object."
        "\n\n**Requires permissions** to edit payments."
        "\n\nErrors:"
        "\n* The passed `OrderLine` does not exist"
    )
