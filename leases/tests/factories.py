import factory

from customers.tests.factories import CustomerProfileFactory
from resources.tests.factories import BerthFactory, WinterStoragePlaceFactory

from ..models import BerthLease, WinterStorageLease


class AbstractLeaseFactory(factory.django.DjangoModelFactory):
    customer = factory.SubFactory(CustomerProfileFactory)
    comment = factory.Faker("text")


class BerthLeaseFactory(AbstractLeaseFactory):
    berth = factory.SubFactory(BerthFactory)

    class Meta:
        model = BerthLease


class WinterStorageLeaseFactory(AbstractLeaseFactory):
    place = factory.SubFactory(WinterStoragePlaceFactory)

    class Meta:
        model = WinterStorageLease
