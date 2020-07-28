import graphene
from graphene_django import DjangoConnectionField, DjangoObjectType

from customers.schema import ProfileNode
from leases.schema import BerthLeaseNode, WinterStorageLeaseNode
from resources.schema import HarborNode, WinterStorageAreaNode
from users.decorators import view_permission_required
from utils.enum import graphene_enum
from utils.schema import CountConnection

from ..enums import (
    AdditionalProductType,
    OrderStatus,
    PeriodType,
    PriceUnits,
    ProductServiceType,
)
from ..models import (
    ADDITIONAL_PRODUCT_TAX_PERCENTAGES,
    AdditionalProduct,
    BerthPriceGroup,
    BerthProduct,
    Order,
    OrderLine,
    OrderLogEntry,
    PLACE_PRODUCT_TAX_PERCENTAGES,
    WinterStorageProduct,
)

PriceUnitsEnum = graphene_enum(PriceUnits)

AdditionalProductTypeEnum = graphene_enum(AdditionalProductType)

ProductServiceTypeEnum = graphene_enum(ProductServiceType)

PeriodTypeEnum = graphene_enum(PeriodType)

PlaceProductTaxEnum = graphene.Enum(
    "PlaceProductTaxEnum",
    [
        (f"TAX_{str(tax).replace('.', '_')}", tax)
        for tax in PLACE_PRODUCT_TAX_PERCENTAGES
    ],
)

AdditionalProductTaxEnum = graphene.Enum(
    "AdditionalProductTaxEnum",
    [
        (f"TAX_{str(tax).replace('.', '_')}", tax)
        for tax in ADDITIONAL_PRODUCT_TAX_PERCENTAGES
    ],
)

OrderStatusEnum = graphene_enum(OrderStatus)

OrderTypeEnum = graphene.Enum(
    "OrderTypeEnum", [("BERTH", "BERTH"), ("WINTER_STORAGE", "WINTER_STORAGE")]
)


class BerthPriceGroupNode(DjangoObjectType):
    name = graphene.String(required=True)
    products = DjangoConnectionField("payments.schema.BerthProductNode", required=True)
    default_product = graphene.Field(
        "payments.schema.BerthProductNode",
        description="Returns the first product associated to the price group "
        "that does not belong to any specific `Harbor`.",
    )

    class Meta:
        model = BerthPriceGroup
        interfaces = (graphene.relay.Node,)
        connection_class = CountConnection

    @classmethod
    @view_permission_required(BerthPriceGroup)
    def get_queryset(cls, queryset, info):
        return super().get_queryset(queryset, info)

    def resolve_default_product(self, info):
        return self.products.filter(harbor__isnull=True).first()


class AbstractPlaceProductNode:
    price_value = graphene.Decimal(required=True)
    price_unit = PriceUnitsEnum(
        required=True, description="`Fixed to PriceUnit.AMOUNT`"
    )
    tax_percentage = PlaceProductTaxEnum(required=True)


class BerthProductNode(DjangoObjectType, AbstractPlaceProductNode):
    price_group = graphene.Field(BerthPriceGroupNode, required=True)
    harbor = graphene.Field(HarborNode)

    class Meta:
        model = BerthProduct
        interfaces = (graphene.relay.Node,)
        connection_class = CountConnection

    @classmethod
    @view_permission_required(BerthProduct)
    def get_queryset(cls, queryset, info):
        return super().get_queryset(queryset, info)


class WinterStorageProductNode(DjangoObjectType, AbstractPlaceProductNode):
    winter_storage_area = graphene.Field(WinterStorageAreaNode)

    class Meta:
        model = WinterStorageProduct
        interfaces = (graphene.relay.Node,)
        connection_class = CountConnection

    @classmethod
    @view_permission_required(WinterStorageProduct)
    def get_queryset(cls, queryset, info):
        return super().get_queryset(queryset, info)


class AdditionalProductNode(DjangoObjectType):
    service = ProductServiceTypeEnum(required=True)
    period = PeriodTypeEnum(required=True)
    price_value = graphene.Decimal(required=True)
    price_unit = PriceUnitsEnum(required=True)
    tax_percentage = AdditionalProductTaxEnum(required=True)
    product_type = AdditionalProductTypeEnum(required=True)

    class Meta:
        model = AdditionalProduct
        interfaces = (graphene.relay.Node,)
        connection_class = CountConnection

    @classmethod
    @view_permission_required(AdditionalProduct)
    def get_queryset(cls, queryset, info):
        return super().get_queryset(queryset, info)


class AdditionalProductServiceNode(graphene.ObjectType):
    service = ProductServiceTypeEnum(required=True)
    product_type = AdditionalProductTypeEnum(required=True)

    class Meta:
        interfaces = (graphene.relay.Node,)
        connection_class = CountConnection

    def resolve_product_type(self, info):
        return (
            AdditionalProductType.FIXED_SERVICE
            if self.service.is_fixed_service()
            else AdditionalProductType.OPTIONAL_SERVICE
        )


class ProductUnion(graphene.Union):
    class Meta:
        types = (BerthProductNode, WinterStorageProductNode)


class LeaseUnion(graphene.Union):
    class Meta:
        types = (BerthLeaseNode, WinterStorageLeaseNode)


class OrderLineNode(DjangoObjectType):
    product = graphene.Field(AdditionalProductNode)
    quantity = graphene.Int(required=True)
    price = graphene.Decimal(required=True)
    tax_percentage = graphene.Decimal(required=True)
    pretax_price = graphene.Decimal(required=True)

    class Meta:
        model = OrderLine
        interfaces = (graphene.relay.Node,)
        connection_class = CountConnection
        exclude = ("order",)

    @classmethod
    @view_permission_required(OrderLine)
    def get_queryset(cls, queryset, info):
        return super().get_queryset(queryset, info)


class OrderLogEntryNode(DjangoObjectType):
    status = OrderStatusEnum(required=True)
    comment = graphene.String()

    class Meta:
        model = OrderLogEntry
        interfaces = (graphene.relay.Node,)
        connection_class = CountConnection
        exclude = ("order",)

    @classmethod
    @view_permission_required(OrderLogEntry)
    def get_queryset(cls, queryset, info):
        return super().get_queryset(queryset, info)


class OrderNode(DjangoObjectType):
    customer = graphene.Field(ProfileNode, required=True)
    product = graphene.Field(ProductUnion)
    lease = graphene.Field(LeaseUnion)
    status = OrderStatusEnum(required=True)
    comment = graphene.String()
    price = graphene.Decimal(required=True)
    tax_percentage = graphene.Decimal(required=True)
    pretax_price = graphene.Decimal(required=True)
    total_price = graphene.Decimal(required=True)
    total_pretax_price = graphene.Decimal(required=True)
    total_tax_percentage = graphene.Decimal(required=True)
    due_date = graphene.Date(required=True)
    order_lines = DjangoConnectionField(OrderLineNode, required=True)
    log_entries = DjangoConnectionField(OrderLogEntryNode, required=True)

    class Meta:
        model = Order
        interfaces = (graphene.relay.Node,)
        connection_class = CountConnection
        exclude = (
            "_product_content_type",
            "_product_object_id",
            "_lease_content_type",
            "_lease_object_id",
        )

    @classmethod
    @view_permission_required(Order)
    def get_queryset(cls, queryset, info):
        return super().get_queryset(queryset, info)
