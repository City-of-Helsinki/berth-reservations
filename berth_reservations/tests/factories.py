import factory
from django.contrib.auth import get_user_model
from munigeo.models import Municipality


class UserFactory(factory.django.DjangoModelFactory):
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    username = factory.Faker("user_name")
    email = factory.Faker("email")

    class Meta:
        model = get_user_model()


class MunicipalityFactory(factory.django.DjangoModelFactory):
    id = factory.Faker("word")
    name = factory.Faker("city")

    class Meta:
        model = Municipality
