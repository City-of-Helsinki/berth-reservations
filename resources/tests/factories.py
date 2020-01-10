import factory
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from factory.random import randgen

from ..enums import BerthMooringType
from ..models import (
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


class AbstractAreaSectionFactory(factory.django.DjangoModelFactory):
    identifier = factory.Faker("random_letter")
    location = factory.LazyFunction(
        lambda: Point(
            24.915 + randgen.uniform(0, 0.040), 60.154 + randgen.uniform(0, 0.022)
        )
    )


class PierFactory(AbstractAreaSectionFactory):
    harbor = factory.SubFactory(HarborFactory)

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
    length = factory.Faker("random_int", min=200, max=2500)
    width = factory.Faker("random_int", min=100, max=300)


class BerthTypeFactory(AbstractPlaceTypeFactory):
    mooring_type = factory.Faker("random_element", elements=list(BerthMooringType))

    class Meta:
        model = BerthType


class WinterStoragePlaceTypeFactory(AbstractPlaceTypeFactory):
    class Meta:
        model = WinterStoragePlaceType


class AbstractPlaceFactory(factory.django.DjangoModelFactory):
    number = factory.LazyFunction(lambda: str(randgen.randint(1, 999)).zfill(2))


class BerthFactory(AbstractPlaceFactory):
    pier = factory.SubFactory(PierFactory)
    berth_type = factory.SubFactory(BerthTypeFactory)

    class Meta:
        model = Berth


class WinterStoragePlaceFactory(AbstractPlaceFactory):
    winter_storage_section = factory.SubFactory(WinterStorageSectionFactory)
    place_type = factory.SubFactory(WinterStoragePlaceTypeFactory)

    class Meta:
        model = WinterStoragePlace


class UserFactory(factory.django.DjangoModelFactory):
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    username = factory.Faker("user_name")
    email = factory.Faker("email")

    class Meta:
        model = get_user_model()
