from django.db import models
from django.utils.translation import gettext_lazy as _

from leases.models import BerthLease, WinterStorageLease
from utils.models import TimeStampedModel

from .enums import ContractStatus


class Contract(TimeStampedModel):
    status = models.CharField(
        choices=ContractStatus.choices,
        max_length=16,
        verbose_name=_("contract status"),
        default=ContractStatus.NEW,
    )

    class Meta:
        abstract = True


class BerthContract(Contract):
    lease = models.OneToOneField(
        BerthLease,
        on_delete=models.SET_NULL,
        related_name="contract",
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True


class WinterStorageContract(Contract):
    lease = models.OneToOneField(
        WinterStorageLease,
        on_delete=models.SET_NULL,
        related_name="contract",
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True


class VismaContract(Contract):
    document_id = models.UUIDField()
    invitation_id = models.UUIDField()
    passphrase = models.CharField(max_length=32)


class VismaBerthContract(VismaContract, BerthContract):
    pass


class VismaWinterStorageContract(VismaContract, WinterStorageContract):
    pass
