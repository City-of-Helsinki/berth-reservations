import factory
from django.contrib.auth import get_user_model
from munigeo.models import Municipality

from customers.enums import InvoicingType
from customers.models import CustomerProfile


class UserFactory(factory.django.DjangoModelFactory):
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    username = factory.Sequence(
        lambda n: factory.Faker("user_name").generate() + f"{n}"
    )
    email = factory.Faker("email")

    class Meta:
        model = get_user_model()


class MunicipalityFactory(factory.django.DjangoModelFactory):
    id = factory.Sequence(lambda n: factory.Faker("word").generate() + f"-{n}")
    name = factory.Faker("city")

    class Meta:
        model = Municipality


class CustomerProfileFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    invoicing_type = factory.Faker("random_element", elements=list(InvoicingType))
    comment = factory.Faker("text")

    class Meta:
        model = CustomerProfile
