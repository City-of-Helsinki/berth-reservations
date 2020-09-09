from graphene import Field, List, Node, String
from graphene_django import DjangoConnectionField

from berth_reservations.exceptions import VenepaikkaGraphQLError
from leases.models import BerthLease, WinterStorageLease

from ..enums import AdditionalProductType, ProductServiceType
from ..models import AdditionalProduct, BerthProduct, Order, WinterStorageProduct
from .types import (
    AdditionalProductNode,
    AdditionalProductServiceNode,
    AdditionalProductTypeEnum,
    BerthPriceGroupNode,
    BerthProductNode,
    OrderDetailsType,
    OrderNode,
    OrderTypeEnum,
    WinterStorageProductNode,
)


class Query:
    berth_price_groups = DjangoConnectionField(
        BerthPriceGroupNode, description="**Requires permissions** to access payments.",
    )
    berth_price_group = Node.Field(
        BerthPriceGroupNode, description="**Requires permissions** to access payments.",
    )

    berth_products = DjangoConnectionField(
        BerthProductNode, description="**Requires permissions** to access payments.",
    )
    berth_product = Node.Field(
        BerthProductNode, description="**Requires permissions** to access payments.",
    )

    winter_storage_products = DjangoConnectionField(
        WinterStorageProductNode,
        description="**Requires permissions** to access payments.",
    )
    winter_storage_product = Node.Field(
        WinterStorageProductNode,
        description="**Requires permissions** to access payments.",
    )

    additional_products = DjangoConnectionField(
        AdditionalProductNode,
        product_type=AdditionalProductTypeEnum(),
        description="**Requires permissions** to access payments.",
    )
    additional_product = Node.Field(
        AdditionalProductNode,
        description="**Requires permissions** to access payments.",
    )
    additional_product_services = List(
        AdditionalProductServiceNode, product_type=AdditionalProductTypeEnum()
    )

    order = Node.Field(
        OrderNode, description="**Requires permissions** to access payments.",
    )
    orders = DjangoConnectionField(
        OrderNode,
        order_type=OrderTypeEnum(),
        description="**Requires permissions** to access payments.",
    )

    def resolve_additional_products(self, info, **kwargs):
        product_type = kwargs.get("product_type")
        if product_type:
            product_type = AdditionalProductType(product_type)
            if product_type == AdditionalProductType.FIXED_SERVICE:
                return AdditionalProduct.objects.filter(
                    service__in=ProductServiceType.FIXED_SERVICES()
                )
            elif product_type == AdditionalProductType.OPTIONAL_SERVICE:
                return AdditionalProduct.objects.filter(
                    service__in=ProductServiceType.OPTIONAL_SERVICES()
                )

        return AdditionalProduct.objects.all()

    def resolve_additional_product_services(self, info, **kwargs):
        service_list = list(ProductServiceType)
        product_type = kwargs.get("product_type")

        if product_type:
            product_type = AdditionalProductType(product_type)
            if product_type == AdditionalProductType.FIXED_SERVICE:
                service_list = ProductServiceType.FIXED_SERVICES()
            elif product_type == AdditionalProductType.OPTIONAL_SERVICE:
                service_list = ProductServiceType.OPTIONAL_SERVICES()

        return [
            AdditionalProductServiceNode(service=service) for service in service_list
        ]

    def resolve_orders(self, info, **kwargs):
        order_type = kwargs.get("order_type")

        if order_type:
            if order_type == "BERTH":
                return Order.objects.berth_orders()
            else:
                return Order.objects.winter_storage_orders()

        return Order.objects.all()


class OldAPIQuery:
    order_details = Field(OrderDetailsType, order_number=String(required=True))

    def resolve_order_details(self, info, order_number):
        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist as e:
            raise VenepaikkaGraphQLError(e)

        order_type = OrderTypeEnum.UNKNOWN
        if order.product:
            if isinstance(order.product, BerthProduct):
                order_type = OrderTypeEnum.BERTH
            elif isinstance(order.product, WinterStorageProduct):
                order_type = OrderTypeEnum.WINTER_STORAGE
        elif order.lease:
            if isinstance(order.lease, BerthLease):
                order_type = OrderTypeEnum.BERTH
            elif isinstance(order.lease, WinterStorageLease):
                order_type = OrderTypeEnum.WINTER_STORAGE

        return OrderDetailsType(status=order.status, order_type=order_type)
