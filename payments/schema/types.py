import graphene
from graphene_django import DjangoConnectionField, DjangoObjectType

from payments.enums import (
    AdditionalProductType,
    PeriodType,
    PriceUnits,
    ProductServiceType,
)
from users.decorators import view_permission_required
from utils.enum import graphene_enum
from utils.schema import CountConnection

from ..models import (
    ADDITIONAL_PRODUCT_TAX_PERCENTAGES,
    AdditionalProduct,
    BerthPriceGroup,
    BerthProduct,
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
    price_group = graphene.Field("payments.schema.BerthPriceGroupNode", required=True)
    harbor = graphene.Field("resources.schema.HarborNode")

    class Meta:
        model = BerthProduct
        interfaces = (graphene.relay.Node,)
        connection_class = CountConnection

    @classmethod
    @view_permission_required(BerthProduct)
    def get_queryset(cls, queryset, info):
        return super().get_queryset(queryset, info)


class WinterStorageProductNode(DjangoObjectType, AbstractPlaceProductNode):
    winter_storage_area = graphene.Field("resources.schema.WinterStorageAreaNode")

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
