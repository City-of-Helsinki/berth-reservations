import graphene
from graphene_django import DjangoConnectionField, DjangoObjectType

from payments.enums import PriceUnits
from users.decorators import view_permission_required
from utils.schema import CountConnection

from ..models import BerthPriceGroup, BerthProduct, TAX_PERCENTAGES

PriceUnitsEnum = graphene.Enum.from_enum(
    PriceUnits, description=lambda e: e.label if e else ""
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


class BerthProductNode(DjangoObjectType):
    price_value = graphene.Decimal(required=True)
    price_unit = PriceUnitsEnum(
        required=True, description="`Fixed to PriceUnit.AMOUNT`"
    )
    tax_percentage = graphene.Decimal(
        required=True,
        description=f"Takes the following options:\n\n"
        f"{', '.join([str(p)+'%' for p in TAX_PERCENTAGES])}",
    )
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
