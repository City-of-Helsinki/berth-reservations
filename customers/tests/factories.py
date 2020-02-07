import factory

from berth_reservations.tests.factories import CustomerProfileFactory
from resources.tests.factories import BoatTypeFactory

from ..models import Boat


class BoatFactory(factory.django.DjangoModelFactory):
    owner = factory.SubFactory(CustomerProfileFactory)
    boat_type = factory.SubFactory(BoatTypeFactory)
    registration_number = factory.Faker("bs")
    name = factory.Faker("bs")
    # even though these are decimals, Faker uses ints for generation ¯\_(ツ)_/¯
    length = factory.Faker("pydecimal", min_value=0, max_value=999)
    width = factory.Faker("pydecimal", min_value=0, max_value=999)

    class Meta:
        model = Boat
