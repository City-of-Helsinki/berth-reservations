import graphene
from graphene_django import DjangoConnectionField, DjangoObjectType

from customers.schema import ProfileNode
from leases.schema import BerthLeaseNode, WinterStorageLeaseNode
from resources.schema import WinterStorageAreaNode
from users.decorators import view_permission_required
from utils.schema import CountConnection

from ..enums import (
    AdditionalProductType,
    OrderStatus,
    PeriodType,
    PriceTier,
    PriceUnits,
    ProductServiceType,
)
from ..models import (
    ADDITIONAL_PRODUCT_TAX_PERCENTAGES,
    AdditionalProduct,
    BerthProduct,
    Order,
    OrderLine,
    OrderLogEntry,
    PLACE_PRODUCT_TAX_PERCENTAGES,
    WinterStorageProduct,
)

PriceUnitsEnum = graphene.Enum.from_enum(PriceUnits)
PriceTierEnum = graphene.Enum.from_enum(PriceTier)
AdditionalProductTypeEnum = graphene.Enum.from_enum(AdditionalProductType)
ProductServiceTypeEnum = graphene.Enum.from_enum(ProductServiceType)
PeriodTypeEnum = graphene.Enum.from_enum(PeriodType)
OrderStatusEnum = graphene.Enum.from_enum(OrderStatus)
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
OrderTypeEnum = graphene.Enum(
    "OrderTypeEnum",
    [
        ("BERTH", "BERTH"),
        ("WINTER_STORAGE", "WINTER_STORAGE"),
        ("ADDITIONAL_PRODUCT", "ADDITIONAL_PRODUCT"),
        ("UNKNOWN", "UNKNOWN"),
    ],
)


class AbstractPlaceProductNode:
    price_value = graphene.Decimal(required=True)
    price_unit = PriceUnitsEnum(
        required=True, description="`Fixed to PriceUnit.AMOUNT`"
    )
    tax_percentage = PlaceProductTaxEnum(required=True)


class BerthProductNode(DjangoObjectType):
    min_width = graphene.Decimal(required=True, description="Excluded from the range")
    max_width = graphene.Decimal(required=True, description="Included in the range")
    tier_1_price = graphene.Decimal(required=True)
    tier_2_price = graphene.Decimal(required=True)
    tier_3_price = graphene.Decimal(required=True)
    tax_percentage = PlaceProductTaxEnum(required=True)
    price_unit = PriceUnitsEnum(
        required=True, description="`Fixed to PriceUnit.AMOUNT`"
    )

    class Meta:
        model = BerthProduct
        interfaces = (graphene.relay.Node,)
        connection_class = CountConnection
        description = "The width range excludes the min width and includes the max width, i.e. `(min, max]`"

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
            if self.service in ProductServiceType.FIXED_SERVICES()
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
    paid_at = graphene.DateTime()
    cancelled_at = graphene.DateTime()

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


class OrderDetailsType(graphene.ObjectType):
    order_type = OrderTypeEnum(required=True)
    status = OrderStatusEnum(required=True)


class FailedOrderType(graphene.ObjectType):
    id = graphene.ID(required=True)
    error = graphene.String()
