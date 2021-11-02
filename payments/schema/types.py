import graphene
from graphene_django import DjangoConnectionField, DjangoObjectType
from graphql_jwt.decorators import login_required

from applications.models import BerthApplication
from customers.models import CustomerProfile
from customers.schema import ProfileNode
from leases.models import BerthLease, WinterStorageLease
from leases.schema import BerthLeaseNode, WinterStorageLeaseNode
from resources.schema import WinterStorageAreaNode
from users.decorators import view_permission_required
from utils.relay import (
    return_node_if_user_has_permissions,
    return_queryset_if_user_has_permissions,
)
from utils.schema import CountConnection

from ..enums import (
    AdditionalProductType,
    OfferStatus,
    OrderRefundStatus,
    OrderStatus,
    PeriodType,
    PriceTier,
    PriceUnits,
    PricingCategory,
    ProductServiceType,
)
from ..models import (
    ADDITIONAL_PRODUCT_TAX_PERCENTAGES,
    AdditionalProduct,
    BerthProduct,
    BerthSwitchOffer,
    Order,
    OrderLine,
    OrderLogEntry,
    OrderRefund,
    PLACE_PRODUCT_TAX_PERCENTAGES,
    WinterStorageProduct,
)

PriceUnitsEnum = graphene.Enum.from_enum(PriceUnits)
PriceTierEnum = graphene.Enum.from_enum(PriceTier)
AdditionalProductTypeEnum = graphene.Enum.from_enum(AdditionalProductType)
ProductServiceTypeEnum = graphene.Enum.from_enum(ProductServiceType)
PeriodTypeEnum = graphene.Enum.from_enum(PeriodType)
OrderStatusEnum = graphene.Enum.from_enum(OrderStatus)
OrderRefundStatusEnum = graphene.Enum.from_enum(OrderRefundStatus)
OfferStatusEnum = graphene.Enum.from_enum(OfferStatus)
PricingCategoryEnum = graphene.Enum.from_enum(PricingCategory)
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
    pricing_category = PricingCategoryEnum(required=True)

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
    due_date = graphene.Date()
    order_lines = DjangoConnectionField(OrderLineNode, required=True)
    log_entries = DjangoConnectionField(OrderLogEntryNode, required=True)
    paid_at = graphene.DateTime(
        description="Date when the order was paid (if it has been paid)"
    )
    cancelled_at = graphene.DateTime(
        description="Date when the order was cancelled by the admins"
    )
    rejected_at = graphene.DateTime(
        description="Date when the order was rejected by the customer"
    )

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
    @login_required
    def get_queryset(cls, queryset, info):
        user = info.context.user
        return return_queryset_if_user_has_permissions(
            queryset,
            user,
            Order,
            BerthLease,
            WinterStorageLease,
            CustomerProfile,
        )

    @classmethod
    @login_required
    def get_node(cls, info, id):
        node = super().get_node(info, id)
        return return_node_if_user_has_permissions(
            node,
            info.context.user,
            Order,
            CustomerProfile,
            BerthLease,
            WinterStorageLease,
        )


class OrderRefundNode(DjangoObjectType):
    order = graphene.Field(OrderNode, required=True)
    refund_id = graphene.String()
    status = OrderRefundStatusEnum(required=True)
    amount = graphene.Decimal(required=True)

    class Meta:
        model = OrderRefund
        interfaces = (graphene.relay.Node,)
        connection_class = CountConnection

    @classmethod
    @login_required
    def get_queryset(cls, queryset, info):
        user = info.context.user
        return return_queryset_if_user_has_permissions(
            queryset,
            user,
            Order,
            OrderRefund,
        )


class AbstractOfferNode:
    customer = graphene.Field(ProfileNode, required=True)
    status = OfferStatusEnum(required=True)
    due_date = graphene.Date()
    customer_first_name = graphene.String()
    customer_last_name = graphene.String()
    customer_email = graphene.String()
    customer_phone = graphene.String()


class BerthSwitchOfferNode(DjangoObjectType, AbstractOfferNode):
    application = graphene.Field(
        "applications.schema.BerthApplicationNode", required=True
    )
    lease = graphene.Field(BerthLeaseNode, required=True)
    berth = graphene.Field("resources.schema.BerthNode", required=True)

    class Meta:
        model = BerthSwitchOffer
        interfaces = (graphene.relay.Node,)
        connection_class = CountConnection

    @classmethod
    @login_required
    def get_queryset(cls, queryset, info):
        user = info.context.user
        return return_queryset_if_user_has_permissions(
            queryset,
            user,
            BerthSwitchOffer,
            BerthLease,
            BerthApplication,
        )

    @classmethod
    @login_required
    def get_node(cls, info, id):
        node = super().get_node(info, id)
        user = info.context.user
        return return_node_if_user_has_permissions(
            node, user, BerthSwitchOffer, BerthLease, BerthApplication
        )


class OrderDetailsType(graphene.ObjectType):
    order_type = OrderTypeEnum(required=True)
    status = OrderStatusEnum(required=True)
    place = graphene.String()  # (berth/ws place number)
    section = graphene.String()  # (pier/section identifier)
    area = graphene.String()  # (harbor/ws area name)
    is_application_order = graphene.Boolean(required=True)


class OfferDetailsType(graphene.ObjectType):
    status = OfferStatusEnum(required=True)
    harbor = graphene.String(required=True)
    pier = graphene.String(required=True)
    berth = graphene.String(required=True)


class GenericErrorType(graphene.ObjectType):
    id = graphene.ID(required=True)
    error = graphene.String()


class FailedOrderType(GenericErrorType):
    pass


class FailedOfferType(GenericErrorType):
    pass
