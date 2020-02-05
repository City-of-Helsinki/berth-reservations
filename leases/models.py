from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _
from enumfields import EnumField

from applications.models import BerthApplication, WinterStorageApplication
from customers.models import Boat, CustomerProfile
from resources.models import Berth, WinterStoragePlace
from utils.models import TimeStampedModel, UUIDModel

from .enums import LeaseStatus


class AbstractLease(TimeStampedModel, UUIDModel):
    customer = models.ForeignKey(
        CustomerProfile, verbose_name=_("customer"), on_delete=models.PROTECT
    )
    boat = models.ForeignKey(
        Boat, verbose_name=_("customer's boat"), on_delete=models.PROTECT
    )

    status = EnumField(
        LeaseStatus,
        verbose_name=_("lease status"),
        max_length=30,
        default=LeaseStatus.OFFERED,
    )

    start_date = models.DateField(verbose_name=_("start date"))
    end_date = models.DateField(verbose_name=_("end date"))

    comment = models.TextField(verbose_name=_("comment"), blank=True)

    class Meta:
        abstract = True

    def clean(self):
        if not self.boat.owner == self.customer:
            raise ValidationError(
                _("The boat should belong to the customer who is creating the lease")
            )

    def save(self, *args, **kwargs):
        # ensure full_clean is always ran
        self.full_clean()

        # this relies on the related_name="changes" for both
        # BerthLeaseChange.lease and WinterStorageLeaseChange.lease
        if not self._state.adding:
            original = type(self).objects.get(pk=self.pk)
            if original.status != self.status:
                self.changes.create(from_status=original.status, to_status=self.status)
        super().save(*args, **kwargs)


class BerthLease(AbstractLease):
    berth = models.ForeignKey(
        Berth, verbose_name=_("berth"), on_delete=models.PROTECT, related_name="leases"
    )
    application = models.OneToOneField(
        BerthApplication,
        verbose_name=_("application"),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="lease",
    )

    class Meta:
        verbose_name = _("berth lease")
        verbose_name_plural = _("berth leases")
        default_related_name = "berth_leases"

    def __str__(self):
        return " {} > {} - {} ({})".format(
            self.berth, self.start_date, self.end_date, self.status
        )


class WinterStorageLease(AbstractLease):
    place = models.ForeignKey(
        WinterStoragePlace,
        verbose_name=_("place"),
        on_delete=models.PROTECT,
        related_name="leases",
    )
    application = models.OneToOneField(
        WinterStorageApplication,
        verbose_name=_("application"),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="lease",
    )

    class Meta:
        verbose_name = _("winter storage lease")
        verbose_name_plural = _("winter storage leases")
        default_related_name = "winter_storage_leases"

    def __str__(self):
        return " {} > {} - {} ({})".format(
            self.place, self.start_date, self.end_date, self.status
        )


class AbstractLeaseChange(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("time created"))
    from_status = EnumField(LeaseStatus, verbose_name=_("from status"), max_length=30)
    to_status = EnumField(LeaseStatus, verbose_name=_("to status"), max_length=30)

    class Meta:
        abstract = True

    def __str__(self):
        return "Lease {}: {} -> {}".format(
            self.lease.id, self.from_status, self.to_status
        )


class BerthLeaseChange(AbstractLeaseChange):
    lease = models.ForeignKey(
        BerthLease,
        verbose_name=_("lease"),
        on_delete=models.CASCADE,
        related_name="changes",
    )

    class Meta:
        verbose_name = _("berth lease change")
        verbose_name_plural = _("berth lease changes")


class WinterStorageLeaseChange(AbstractLeaseChange):
    lease = models.ForeignKey(
        WinterStorageLease,
        verbose_name=_("lease"),
        on_delete=models.CASCADE,
        related_name="changes",
    )

    class Meta:
        verbose_name = _("winter storage lease change")
        verbose_name_plural = _("winter storage lease changes")
