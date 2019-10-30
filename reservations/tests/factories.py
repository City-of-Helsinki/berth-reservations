import factory.fuzzy

from harbors.tests.factories import (
    BoatTypeFactory,
    HarborFactory,
    WinterStorageAreaFactory,
)

from ..enums import WinterStorageMethod
from ..models import (
    BerthReservation,
    HarborChoice,
    WinterStorageAreaChoice,
    WinterStorageReservation,
)


class BaseReservationFactory(factory.django.DjangoModelFactory):
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Faker("email")
    boat_type = factory.SubFactory(BoatTypeFactory)
    boat_length = factory.fuzzy.FuzzyDecimal(0.1, 100.00)
    boat_width = factory.fuzzy.FuzzyDecimal(0.1, 100.00)


class BerthReservationFactory(BaseReservationFactory):
    class Meta:
        model = BerthReservation


class WinterStorageReservationFactory(BaseReservationFactory):
    storage_method = WinterStorageMethod.ON_TRAILER

    class Meta:
        model = WinterStorageReservation


class HarborChoiceFactory(factory.django.DjangoModelFactory):
    harbor = factory.SubFactory(HarborFactory)
    reservation = factory.SubFactory(BerthReservationFactory)
    priority = factory.Faker("random_int", min=1, max=10)

    class Meta:
        model = HarborChoice


class WinterAreaChoiceFactory(factory.django.DjangoModelFactory):
    winter_storage_area = factory.SubFactory(WinterStorageAreaFactory)
    reservation = factory.SubFactory(WinterStorageReservationFactory)
    priority = factory.Faker("random_int", min=1, max=10)

    class Meta:
        model = WinterStorageAreaChoice
