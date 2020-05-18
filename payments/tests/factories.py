import random
from decimal import Decimal

import factory

from resources.tests.factories import HarborFactory, WinterStorageAreaFactory

from ..enums import PeriodType, PriceUnits, ServiceType
from ..models import (
    AbstractBaseProduct,
    AdditionalProduct,
    BerthPriceGroup,
    BerthProduct,
    DEFAULT_TAX_PERCENTAGE,
    TAX_PERCENTAGES,
    WinterStorageProduct,
)


class AbstractBaseProductFactory(factory.django.DjangoModelFactory):
    price_value = factory.LazyFunction(
        lambda: round(Decimal(random.uniform(1, 999)), 2)
    )
    price_unit = factory.Faker("random_element", elements=list(PriceUnits))
    tax_percentage = factory.Faker("random_element", elements=TAX_PERCENTAGES)

    class Meta:
        model = AbstractBaseProduct


class BerthPriceGroupFactory(factory.django.DjangoModelFactory):
    name = factory.Faker("word")

    class Meta:
        model = BerthPriceGroup


class AbstractPlaceProductFactory(AbstractBaseProductFactory):
    price_unit = factory.LazyFunction(lambda: PriceUnits.AMOUNT)
    tax_percentage = factory.LazyFunction(lambda: DEFAULT_TAX_PERCENTAGE)


class BerthProductFactory(AbstractPlaceProductFactory):
    price_group = factory.SubFactory(BerthPriceGroupFactory)
    harbor = factory.SubFactory(HarborFactory)

    class Meta:
        model = BerthProduct


class WinterStorageProductFactory(AbstractPlaceProductFactory):
    winter_storage_area = factory.SubFactory(WinterStorageAreaFactory)

    class Meta:
        model = WinterStorageProduct


class AdditionalProductFactory(AbstractBaseProductFactory):
    service = factory.Faker("random_element", elements=list(ServiceType))
    period = factory.Faker("random_element", elements=list(PeriodType))

    class Meta:
        model = AdditionalProduct
