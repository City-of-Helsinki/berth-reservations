from graphene import Node
from graphene_django import DjangoConnectionField

from payments.enums import AdditionalProductType, ServiceType
from payments.models import AdditionalProduct

from .types import (
    AdditionalProductNode,
    AdditionalProductTypeEnum,
    BerthPriceGroupNode,
    BerthProductNode,
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

    def resolve_additional_products(self, info, **kwargs):
        product_type = kwargs.get("product_type")
        if product_type:
            product_type = AdditionalProductType(product_type)
            if product_type == AdditionalProductType.FIXED_SERVICE:
                return AdditionalProduct.objects.filter(
                    service__in=ServiceType.FIXED_SERVICES()
                )
            elif product_type == AdditionalProductType.OPTIONAL_SERVICE:
                return AdditionalProduct.objects.filter(
                    service__in=ServiceType.OPTIONAL_SERVICES()
                )

        return AdditionalProduct.objects.all()