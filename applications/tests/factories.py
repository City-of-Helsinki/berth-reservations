import factory.fuzzy

from harbors.tests.factories import (
    BoatTypeFactory,
    HarborFactory,
    WinterStorageAreaFactory,
)

from ..enums import WinterStorageMethod
from ..models import (
    BerthApplication,
    BerthSwitch,
    HarborChoice,
    WinterStorageApplication,
    WinterStorageAreaChoice,
)


class BaseApplicationFactory(factory.django.DjangoModelFactory):
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Faker("email")
    boat_type = factory.SubFactory(BoatTypeFactory)
    boat_length = factory.fuzzy.FuzzyDecimal(0.1, 100.00)
    boat_width = factory.fuzzy.FuzzyDecimal(0.1, 100.00)
    phone_number = factory.Faker("phone_number")
    address = factory.Faker("address")
    zip_code = factory.Faker("zipcode")
    municipality = factory.Faker("word")


class BerthApplicationFactory(BaseApplicationFactory):
    class Meta:
        model = BerthApplication


class WinterStorageApplicationFactory(BaseApplicationFactory):
    storage_method = WinterStorageMethod.ON_TRAILER

    class Meta:
        model = WinterStorageApplication


class HarborChoiceFactory(factory.django.DjangoModelFactory):
    harbor = factory.SubFactory(HarborFactory)
    application = factory.SubFactory(BerthApplicationFactory)
    priority = factory.Faker("random_int", min=1, max=10)

    class Meta:
        model = HarborChoice


class WinterAreaChoiceFactory(factory.django.DjangoModelFactory):
    winter_storage_area = factory.SubFactory(WinterStorageAreaFactory)
    application = factory.SubFactory(WinterStorageApplicationFactory)
    priority = factory.Faker("random_int", min=1, max=10)

    class Meta:
        model = WinterStorageAreaChoice


class BerthSwitchFactory(factory.django.DjangoModelFactory):
    harbor = factory.SubFactory(HarborFactory)
    pier = factory.Faker("random_int", min=1, max=100)
    berth_number = factory.Faker("random_int", min=1, max=100)

    class Meta:
        model = BerthSwitch
