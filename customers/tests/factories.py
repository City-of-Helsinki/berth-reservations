import factory

from berth_reservations.tests.factories import CustomerProfileFactory
from resources.tests.factories import BoatTypeFactory

from ..models import Boat, Organization


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


class OrganizationFactory(factory.django.DjangoModelFactory):
    customer = factory.SubFactory(CustomerProfileFactory)
    business_id = factory.Faker("company_business_id", locale="fi_FI")
    name = factory.Faker("company")
    address = factory.Faker("street_address")
    postal_code = factory.Faker("postcode")
    city = factory.Faker("city")

    class Meta:
        model = Organization
