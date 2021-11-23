import factory.fuzzy

from customers.tests.factories import BoatFactory
from resources.tests.factories import (
    BerthFactory,
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
    email = factory.Sequence(
        lambda n: "application{}@example.org".format(n)
    )  # example.com is not valid
    phone_number = factory.Sequence(lambda n: "+%03d%09d" % (n // 10000, n % 10000))
    address = factory.Faker("address")
    zip_code = factory.Faker("zipcode")
    municipality = factory.Faker("word")
    customer = None  # required by the SelfAttribute below
    boat = factory.SubFactory(BoatFactory, owner=factory.SelfAttribute("..customer"))


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
    priority = factory.fuzzy.FuzzyInteger(1, 10)

    class Meta:
        model = HarborChoice


class WinterAreaChoiceFactory(factory.django.DjangoModelFactory):
    winter_storage_area = factory.SubFactory(WinterStorageAreaFactory)
    application = factory.SubFactory(WinterStorageApplicationFactory)
    priority = factory.fuzzy.FuzzyInteger(1, 10)

    class Meta:
        model = WinterStorageAreaChoice


class BerthSwitchFactory(factory.django.DjangoModelFactory):
    berth = factory.SubFactory(BerthFactory)

    class Meta:
        model = BerthSwitch
