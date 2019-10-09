import factory.fuzzy

from ..enums import WinterStorageMethod
from ..models import BerthReservation, WinterStorageReservation


class BaseReservationFactory(factory.django.DjangoModelFactory):
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Faker("email")
    boat_length = factory.fuzzy.FuzzyDecimal(0.1, 100.00)
    boat_width = factory.fuzzy.FuzzyDecimal(0.1, 100.00)


class BerthReservationFactory(BaseReservationFactory):
    class Meta:
        model = BerthReservation


class WinterStorageReservationFactory(BaseReservationFactory):
    storage_method = WinterStorageMethod.ON_TRAILER

    class Meta:
        model = WinterStorageReservation
