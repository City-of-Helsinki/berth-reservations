import factory
from django.db.models.signals import post_save

from berth_reservations.tests.factories import CustomerProfileFactory
from customers.tests.factories import BoatFactory
from resources.tests.factories import BerthFactory, WinterStoragePlaceFactory

from ..models import BerthLease, WinterStorageLease
from .utils import create_berth_products, create_winter_storage_product


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

    @factory.post_generation
    def create_product(obj, create, extracted, **kwargs):
        """When creating a lease, create all the necessary products for that berth"""
        if extracted is not False:
            create_berth_products(obj.berth, create)

    class Meta:
        model = BerthLease


@factory.django.mute_signals(post_save)
class WinterStorageLeaseFactory(AbstractLeaseFactory):
    place = factory.SubFactory(WinterStoragePlaceFactory)
    contract = factory.SubFactory(
        "contracts.tests.factories.WinterStorageContractFactory", lease=None,
    )

    @factory.post_generation
    def create_product(obj, create, extracted, **kwargs):
        """When creating a lease, create all the necessary products for that berth"""
        if extracted is not False:
            create_winter_storage_product(obj.get_winter_storage_area(), create)

    class Meta:
        model = WinterStorageLease
