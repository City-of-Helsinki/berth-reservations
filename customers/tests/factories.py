import factory

from users.tests.factories import UserFactory

from ..enums import InvoicingType
from ..models import CustomerProfile


class CustomerProfileFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    invoicing_type = factory.Faker("random_element", elements=list(InvoicingType))
    comment = factory.Faker("text")

    class Meta:
        model = CustomerProfile
