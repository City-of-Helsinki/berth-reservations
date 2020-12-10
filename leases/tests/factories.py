import factory
from django.db.models.signals import post_save

from berth_reservations.tests.factories import CustomerProfileFactory
from customers.tests.factories import BoatFactory
from resources.tests.factories import BerthFactory, WinterStoragePlaceFactory

from ..models import BerthLease, WinterStorageLease


class AbstractLeaseFactory(factory.django.DjangoModelFactory):
    comment = factory.Faker("text")
    boat = factory.SubFactory(BoatFactory, owner=factory.SelfAttribute("..customer"))
    customer = factory.SubFactory(CustomerProfileFactory)


@factory.django.mute_signals(post_save)
class BerthLeaseFactory(AbstractLeaseFactory):
    berth = factory.SubFactory(BerthFactory)
    contract = factory.SubFactory(
        "contracts.tests.factories.BerthContractFactory", lease=None,
    )

    class Meta:
        model = BerthLease


@factory.django.mute_signals(post_save)
class WinterStorageLeaseFactory(AbstractLeaseFactory):
    place = factory.SubFactory(WinterStoragePlaceFactory)
    contract = factory.SubFactory(
        "contracts.tests.factories.WinterStorageContractFactory", lease=None,
    )

    class Meta:
        model = WinterStorageLease
