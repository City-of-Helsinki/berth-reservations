from datetime import date

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import ExpressionWrapper, Q
from django.utils.translation import ugettext_lazy as _
from enumfields import EnumField

from applications.models import BerthApplication, WinterStorageApplication
from customers.models import Boat, CustomerProfile
from resources.models import Berth, WinterStoragePlace
from utils.models import TimeStampedModel, UUIDModel

from .consts import ACTIVE_LEASE_STATUSES
from .enums import LeaseStatus
from .utils import calculate_berth_lease_end_date, calculate_berth_lease_start_date


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
        if self.start_date > self.end_date:
            raise ValidationError(_("Lease start date cannot be after end date"))

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


class BerthLeaseManager(models.Manager):
    def get_queryset(self):
        current_season_start = calculate_berth_lease_start_date()
        today = date.today()

        active_current_status = Q(status=LeaseStatus.PAID)

        if today < current_season_start:
            in_current_season = Q(start_date=current_season_start)
        else:
            in_current_season = Q(start_date__lte=today) & Q(end_date__gte=today)

        return (
            super()
            .get_queryset()
            .annotate(
                is_active=ExpressionWrapper(
                    in_current_season & active_current_status,
                    output_field=models.BooleanField(),
                )
            )
        )


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
    renew_automatically = models.BooleanField(
        verbose_name=_("renew automatically"), default=True
    )
    objects = BerthLeaseManager()

    class Meta:
        verbose_name = _("berth lease")
        verbose_name_plural = _("berth leases")
        default_related_name = "berth_leases"

    def clean(self):
        if self.start_date.year != self.end_date.year:
            raise ValidationError(
                _("BerthLease start and end year have to be the same")
            )
        leases_for_given_period = BerthLease.objects.filter(
            berth=self.berth,
            end_date__gte=self.start_date,
            status__in=ACTIVE_LEASE_STATUSES,
        )
        creating = self._state.adding
        if not creating:
            old_instance = BerthLease.objects.get(id=self.id)
            # If the berth is being changed
            if old_instance.berth != self.berth:
                raise ValidationError(
                    _("Cannot change the berth assigned to this lease")
                )
            # If the application is being changed, it has to belong to the same customer
            if (
                self.application
                and old_instance.application
                and old_instance.application.customer != self.application.customer
            ):
                raise ValidationError(
                    _(
                        "Cannot change the application to one which belongs to another customer"
                    )
                )
            leases_for_given_period = leases_for_given_period.exclude(pk=self.pk)
        if leases_for_given_period.exists():
            raise ValidationError(_("Berth already has a lease"))
        if not self.berth.is_active and creating:
            raise ValidationError(_("Selected berth is not active"))
        super().clean()

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

    def clean(self):
        existing_leases = WinterStorageLease.objects.filter(
            place=self.place,
            end_date__gte=self.start_date,
            status__in=ACTIVE_LEASE_STATUSES,
        )
        creating = self._state.adding
        if not creating:
            # If the place is being changed
            if not WinterStorageLease.objects.filter(
                id=self.id, place=self.place
            ).exists():
                raise ValidationError(
                    _("Cannot change the place assigned to this lease")
                )
            existing_leases = existing_leases.exclude(pk=self.pk)
        if existing_leases.exists():
            raise ValidationError(_("WinterStoragePlace already has a lease"))
        if not self.place.is_active and creating:
            raise ValidationError(_("Selected place is not active"))
        super().clean()

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
