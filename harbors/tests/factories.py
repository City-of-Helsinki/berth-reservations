import factory
from django.contrib.gis.geos import Point
from factory.random import randgen

from ..models import BoatType, Harbor, WinterStorageArea


class BoatTypeFactory(factory.django.DjangoModelFactory):
    name = factory.Faker("word")

    class Meta:
        model = BoatType


class AbstractAreaFactory(factory.django.DjangoModelFactory):
    servicemap_id = factory.LazyFunction(lambda: str(randgen.randint(1, 99999)))
    zip_code = factory.Faker("postcode", locale="fi_FI")
    name = factory.Faker("word")
    street_address = factory.Faker("address")
    location = factory.LazyFunction(
        lambda: Point(
            24.915 + randgen.uniform(0, 0.040), 60.154 + randgen.uniform(0, 0.022)
        )
    )


class HarborFactory(AbstractAreaFactory):
    class Meta:
        model = Harbor


class WinterStorageAreaFactory(AbstractAreaFactory):
    class Meta:
        model = WinterStorageArea
