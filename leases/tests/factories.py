from datetime import date, timedelta

import factory
from factory.random import randgen

from customers.tests.factories import CustomerProfileFactory
from resources.tests.factories import BerthFactory, WinterStoragePlaceFactory

from ..models import BerthLease, WinterStorageLease


class AbstractLeaseFactory(factory.django.DjangoModelFactory):
    customer = factory.SubFactory(CustomerProfileFactory)
    comment = factory.Faker("text")
    start_date = factory.LazyFunction(
        lambda: date.today() + timedelta(days=randgen.randint(1, 30))
    )
    end_date = factory.LazyAttribute(
        lambda l: l.start_date + timedelta(days=randgen.randint(60, 180))
    )


class BerthLeaseFactory(AbstractLeaseFactory):
    berth = factory.SubFactory(BerthFactory)

    class Meta:
        model = BerthLease


class WinterStorageLeaseFactory(AbstractLeaseFactory):
    place = factory.SubFactory(WinterStoragePlaceFactory)

    class Meta:
        model = WinterStorageLease
