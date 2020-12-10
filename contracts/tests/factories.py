import factory
from django.db.models.signals import post_save

from leases.tests.factories import BerthLeaseFactory, WinterStorageLeaseFactory

from ..enums import ContractStatus
from ..models import (
    Contract,
    VismaBerthContract,
    VismaContract,
    VismaWinterStorageContract,
)


class ContractFactory(factory.django.DjangoModelFactory):
    status = factory.Faker("random_element", elements=ContractStatus.values)

    class Meta:
        model = Contract


class VismaContractFactory(ContractFactory):
    document_id = factory.Faker("uuid4")
    invitation_id = factory.Faker("uuid4")
    passphrase = factory.Faker("lexify", text="????????")

    class Meta:
        model = VismaContract


@factory.django.mute_signals(post_save)
class BerthContractFactory(VismaContractFactory):
    lease = factory.RelatedFactory(BerthLeaseFactory, factory_related_name="contract")

    class Meta:
        model = VismaBerthContract


@factory.django.mute_signals(post_save)
class WinterStorageContractFactory(VismaContractFactory):
    lease = factory.RelatedFactory(
        WinterStorageLeaseFactory, factory_related_name="contract"
    )

    class Meta:
        model = VismaWinterStorageContract
