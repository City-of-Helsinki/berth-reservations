import string

import factory
from django.contrib.gis.geos import Point
from factory.random import randgen

from payments.enums import PriceTier

from ..enums import AreaRegion, BerthMooringType
from ..models import (
    AvailabilityLevel,
    Berth,
    BerthType,
    BoatType,
    Harbor,
    Pier,
    WinterStorageArea,
    WinterStoragePlace,
    WinterStoragePlaceType,
    WinterStorageSection,
)


class AvailabilityLevelFactory(factory.django.DjangoModelFactory):
    title = factory.Faker("word")
    description = factory.Faker("sentence")

    class Meta:
        model = AvailabilityLevel


class BoatTypeFactory(factory.django.DjangoModelFactory):
    name = factory.Faker("word")

    class Meta:
        model = BoatType


class AbstractAreaFactory(factory.django.DjangoModelFactory):
    servicemap_id = factory.Sequence(lambda n: f"{randgen.randint(39000, 42000)}{n}")
    zip_code = factory.Faker("postcode", locale="fi_FI")
    name = factory.Faker("word")
    street_address = factory.Faker("address")
    region = factory.Faker("random_element", elements=AreaRegion.values)
    location = factory.LazyFunction(
        lambda: Point(
            24.915 + randgen.uniform(0, 0.040), 60.154 + randgen.uniform(0, 0.022)
        )
    )


class HarborFactory(AbstractAreaFactory):
    image_file = factory.LazyAttribute(
        lambda h: f"/img/helsinki_harbors/{h.servicemap_id}.jpg"
    )

    class Meta:
        model = Harbor


class WinterStorageAreaFactory(AbstractAreaFactory):
    class Meta:
        model = WinterStorageArea


class AbstractAreaSectionFactory(factory.django.DjangoModelFactory):
    identifier = factory.Sequence(
        lambda x: string.ascii_lowercase[x % len(string.ascii_lowercase)]
    )
    location = factory.LazyFunction(
        lambda: Point(
            24.915 + randgen.uniform(0, 0.040), 60.154 + randgen.uniform(0, 0.022)
        )
    )


class PierFactory(AbstractAreaSectionFactory):
    harbor = factory.SubFactory(HarborFactory)
    personal_electricity = factory.Faker("boolean")
    price_tier = factory.Faker("random_element", elements=PriceTier.values)

    class Meta:
        model = Pier

    @factory.post_generation
    def suitable_boat_types(self, created, extracted, **kwargs):
        count = kwargs.pop("count", None)
        if count:
            for bt in BoatTypeFactory.create_batch(count, **kwargs):
                self.suitable_boat_types.add(bt)


class WinterStorageSectionFactory(AbstractAreaSectionFactory):
    area = factory.SubFactory(WinterStorageAreaFactory)

    class Meta:
        model = WinterStorageSection


class AbstractPlaceTypeFactory(factory.django.DjangoModelFactory):
    length = factory.Faker(
        "pydecimal", min_value=0, max_value=99, right_digits=2, positive=True
    )
    width = factory.Faker(
        "pydecimal", min_value=0, max_value=99, right_digits=2, positive=True
    )


class BerthTypeFactory(AbstractPlaceTypeFactory):
    mooring_type = factory.Faker("random_element", elements=list(BerthMooringType))
    depth = factory.Faker(
        "pydecimal", min_value=0, max_value=999, right_digits=2, positive=True
    )

    class Meta:
        model = BerthType


class WinterStoragePlaceTypeFactory(AbstractPlaceTypeFactory):
    class Meta:
        model = WinterStoragePlaceType


class BerthFactory(factory.django.DjangoModelFactory):
    number = factory.LazyFunction(lambda: str(randgen.randint(1, 1_000_000)))
    pier = factory.SubFactory(PierFactory)
    berth_type = factory.SubFactory(BerthTypeFactory)

    class Meta:
        model = Berth


class WinterStoragePlaceFactory(factory.django.DjangoModelFactory):
    number = factory.Faker("random_int")
    winter_storage_section = factory.SubFactory(WinterStorageSectionFactory)
    place_type = factory.SubFactory(WinterStoragePlaceTypeFactory)

    class Meta:
        model = WinterStoragePlace
