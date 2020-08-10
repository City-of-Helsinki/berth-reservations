import factory

from berth_reservations.tests.factories import CustomerProfileFactory
from customers.tests.factories import BoatFactory
from resources.tests.factories import BerthFactory, WinterStoragePlaceFactory

from ..models import BerthLease, WinterStorageLease


class AbstractLeaseFactory(factory.django.DjangoModelFactory):
    comment = factory.Faker("text")
    boat = factory.SubFactory(BoatFactory, owner=factory.SelfAttribute("..customer"))
    customer = factory.SubFactory(CustomerProfileFactory)


class BerthLeaseFactory(AbstractLeaseFactory):
    berth = factory.SubFactory(BerthFactory)

    class Meta:
        model = BerthLease


class WinterStorageLeaseFactory(AbstractLeaseFactory):
    place = factory.SubFactory(WinterStoragePlaceFactory)

    class Meta:
        model = WinterStorageLease
