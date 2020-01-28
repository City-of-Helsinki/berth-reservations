import factory

from resources.tests.factories import BoatTypeFactory
from users.tests.factories import UserFactory

from ..enums import InvoicingType
from ..models import Boat, CustomerProfile


class CustomerProfileFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    invoicing_type = factory.Faker("random_element", elements=list(InvoicingType))
    comment = factory.Faker("text")

    class Meta:
        model = CustomerProfile


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
