from graphene import Node
from graphene_django import DjangoConnectionField

from .types import BerthPriceGroupNode, BerthProductNode


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
