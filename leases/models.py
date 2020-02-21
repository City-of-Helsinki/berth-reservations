from datetime import date

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _
from enumfields import EnumField

from applications.models import BerthApplication, WinterStorageApplication
from customers.models import Boat, CustomerProfile
from resources.models import Berth, WinterStoragePlace
from utils.models import TimeStampedModel, UUIDModel

from .enums import LeaseStatus


# If a lease object is being created before 10.6, then the dates are in the same year.
# If the object is being created between those dates, then the start date is
# the date of creation and end date is 14.9 of the same year.
# If the object is being created after 14.9, then the dates are from next year.
def calculate_berth_lease_start_date():
    # Leases always start on 10.6 the earliest
    today = date.today()
    default = date(day=10, month=6, year=today.year)

    # If today is gte than the date when all the leases end,
    # return the default start date for the next year
    if today >= date(day=14, month=9, year=today.year):
        return default.replace(year=today.year + 1)

    # Otherwise, return the latest date between the default start date or today
    return max(default, today)


def calculate_berth_lease_end_date():
    # Leases always end on 14.9
    today = date.today()
    default = date(day=14, month=9, year=today.year)

    # If today is gte than the day when all leases end,
    # return the default end date for the next year
    if today >= default:
        return default.replace(year=today.year + 1)

    # Otherwise, return the default end date for the current year
    return default


class AbstractLease(TimeStampedModel, UUIDModel):
    customer = models.ForeignKey(
        CustomerProfile, verbose_name=_("customer"), on_delete=models.PROTECT
    )
    boat = models.ForeignKey(
        Boat,
        verbose_name=_("customer's boat"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    status = EnumField(
        LeaseStatus,
        verbose_name=_("lease status"),
        max_length=30,
        default=LeaseStatus.DRAFTED,
    )

    start_date = models.DateField(verbose_name=_("start date"))
    end_date = models.DateField(verbose_name=_("end date"))

    comment = models.TextField(verbose_name=_("comment"), blank=True)

    class Meta:
        abstract = True

    def clean(self):
        if self.boat and not self.boat.owner == self.customer:
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
    start_date = models.DateField(
        verbose_name=_("start date"), default=calculate_berth_lease_start_date
    )
    end_date = models.DateField(
        verbose_name=_("end date"), default=calculate_berth_lease_end_date
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
