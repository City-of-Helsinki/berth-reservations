from graphene import Decimal, Field, ID, List, Node, String
from graphene_django import DjangoConnectionField

from berth_reservations.exceptions import VenepaikkaGraphQLError
from leases.models import BerthLease, WinterStorageLease
from users.decorators import view_permission_required
from utils.relay import from_global_id

from ..enums import AdditionalProductType, OrderType, ProductServiceType
from ..models import (
    AdditionalProduct,
    BerthProduct,
    Order,
    OrderRefund,
    WinterStorageProduct,
)
from .types import (
    AdditionalProductNode,
    AdditionalProductServiceNode,
    AdditionalProductTypeEnum,
    BerthProductNode,
    BerthSwitchOfferNode,
    OrderDetailsType,
    OrderNode,
    OrderRefundNode,
    OrderStatusEnum,
    OrderTypeEnum,
    WinterStorageProductNode,
)


class Query:
    berth_products = DjangoConnectionField(
        BerthProductNode, description="**Requires permissions** to access payments.",
    )
    berth_product = Node.Field(
        BerthProductNode, description="**Requires permissions** to access payments.",
    )
    berth_product_for_width = Field(
        BerthProductNode,
        width=Decimal(required=True),
        description="**Requires permissions** to access payments.",
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
        statuses=List(OrderStatusEnum),
        order_type=OrderTypeEnum(),
        description="**Requires permissions** to access payments.",
    )
    order_refunds = DjangoConnectionField(
        OrderRefundNode,
        order_id=ID(required=True),
        description="Returns the Order Refund objects associated to the order."
        "\n\n**Requires permissions** to access payments.",
    )
    berth_switch_offer = Node.Field(
        BerthSwitchOfferNode, description="**Requires permissions** to access offers.",
    )
    berth_switch_offers = DjangoConnectionField(BerthSwitchOfferNode)

    order_details = Field(OrderDetailsType, order_number=String(required=True))

    @view_permission_required(BerthProduct)
    def resolve_berth_product_for_width(self, info, width, **kwargs):
        return BerthProduct.objects.get_in_range(width)

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

    def resolve_orders(self, info, order_type=None, statuses=None, **kwargs):
        qs = Order.objects.all()
        if order_type:
            if order_type == "BERTH":
                qs = Order.objects.berth_orders()
            else:
                qs = Order.objects.winter_storage_orders()

        if statuses:
            qs = qs.filter(status__in=statuses)
        return qs

    def resolve_order_refunds(self, info, order_id, **kwargs):
        return OrderRefund.objects.filter(order_id=from_global_id(order_id, OrderNode))

    def resolve_order_details(self, info, order_number):
        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist as e:
            raise VenepaikkaGraphQLError(e)

        is_application_order = (
            hasattr(order, "lease")
            and getattr(order.lease, "application", None) is not None
        )

        order_type = Query._get_order_type(order)

        if isinstance(order.lease, BerthLease):
            place_number = order.lease.berth.number
            section_identifier = order.lease.berth.pier.identifier
            area_name = order.lease.berth.pier.harbor.name
        elif isinstance(order.lease, WinterStorageLease):
            if order.lease.place:
                place_number = str(order.lease.place.number)
                section_identifier = order.lease.place.winter_storage_section.identifier
                area_name = order.lease.place.winter_storage_section.area.name
            else:
                # unmarked ws lease
                place_number = None
                section_identifier = order.lease.section.identifier
                area_name = order.lease.section.area.name
        else:
            place_number = None
            section_identifier = None
            area_name = None

        return OrderDetailsType(
            status=order.status,
            order_type=order_type,
            area=area_name,
            section=section_identifier,
            place=place_number,
            is_application_order=is_application_order,
        )

    @staticmethod
    def _get_order_type(order):
        # in graphene-python, all resolvers are implictly staticmethods, so need to make this utility static too.
        order_type = OrderTypeEnum.UNKNOWN
        if order.order_type == OrderType.ADDITIONAL_PRODUCT_ORDER:
            order_type = OrderTypeEnum.ADDITIONAL_PRODUCT
        elif order.product:
            if isinstance(order.product, BerthProduct):
                order_type = OrderTypeEnum.BERTH
            elif isinstance(order.product, WinterStorageProduct):
                order_type = OrderTypeEnum.WINTER_STORAGE
        elif order.lease:
            if isinstance(order.lease, BerthLease):
                order_type = OrderTypeEnum.BERTH
            elif isinstance(order.lease, WinterStorageLease):
                order_type = OrderTypeEnum.WINTER_STORAGE
        return order_type
