from datetime import date

from dateutil.relativedelta import relativedelta
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import ExpressionWrapper, Q
from django.utils.translation import gettext_lazy as _

from applications.models import BerthApplication, WinterStorageApplication
from customers.models import Boat, CustomerProfile
from resources.models import Berth, WinterStoragePlace, WinterStorageSection
from utils.models import TimeStampedModel, UUIDModel

from .consts import ACTIVE_LEASE_STATUSES
from .enums import LeaseStatus
from .utils import (
    calculate_berth_lease_end_date,
    calculate_berth_lease_start_date,
    calculate_winter_storage_lease_end_date,
    calculate_winter_storage_lease_start_date,
)


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

    status = models.CharField(
        choices=LeaseStatus.choices,
        verbose_name=_("lease status"),
        max_length=30,
        default=LeaseStatus.DRAFTED,
    )
    _orders_relation = GenericRelation(
        "payments.Order",
        object_id_field="_lease_object_id",
        content_type_field="_lease_content_type",
    )

    comment = models.TextField(verbose_name=_("comment"), blank=True)

    class Meta:
        abstract = True

    @property
    def order(self):
        return self._orders_relation.first()

    def clean(self):
        if self.boat and self.boat.owner != self.customer:
            raise ValidationError(
                _("The boat should belong to the customer who is creating the lease")
            )
        if self.start_date > self.end_date:
            raise ValidationError(_("Lease start date cannot be after end date"))

        # Check that the lease ends less than a year after it started
        if self.end_date > (self.start_date + relativedelta(years=1)):
            raise ValidationError(_("Lease cannot last for more than a year"))

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
            start_date__lte=self.end_date,
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


class WinterStorageLeaseManager(models.Manager):
    def get_queryset(self):
        current_season_start = calculate_winter_storage_lease_start_date()
        today = date.today()

        is_paid = Q(status=LeaseStatus.PAID)

        if today < current_season_start:
            in_current_season = Q(start_date=current_season_start)
        else:
            in_current_season = Q(start_date__lte=today) & Q(end_date__gte=today)

        return (
            super()
            .get_queryset()
            .annotate(
                is_active=ExpressionWrapper(
                    in_current_season & is_paid, output_field=models.BooleanField(),
                )
            )
        )


class WinterStorageLease(AbstractLease):
    place = models.ForeignKey(
        WinterStoragePlace,
        verbose_name=_("place"),
        on_delete=models.PROTECT,
        related_name="leases",
        null=True,
        blank=True,
    )
    section = models.ForeignKey(
        WinterStorageSection,
        verbose_name=_("section"),
        on_delete=models.PROTECT,
        related_name="leases",
        null=True,
        blank=True,
    )
    application = models.OneToOneField(
        WinterStorageApplication,
        verbose_name=_("application"),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="lease",
    )
    start_date = models.DateField(
        verbose_name=_("start date"), default=calculate_winter_storage_lease_start_date
    )
    end_date = models.DateField(
        verbose_name=_("end date"), default=calculate_winter_storage_lease_end_date
    )
    sticker_number = models.PositiveSmallIntegerField(
        verbose_name=_("sticker number"), null=True, blank=True
    )
    objects = WinterStorageLeaseManager()

    class Meta:
        verbose_name = _("winter storage lease")
        verbose_name_plural = _("winter storage leases")
        default_related_name = "winter_storage_leases"

    def clean(self):
        creating = self._state.adding

        if self.place and self.section:
            raise ValidationError(
                _("Lease cannot have both place and section assigned")
            )
        elif not self.place and not self.section:
            raise ValidationError(_("Lease must have either place or section assigned"))

        if not creating:
            old_instance = WinterStorageLease.objects.get(id=self.id)

            # Check that the place/section are not being changed
            self._check_lease_place(old_instance)
            # Check that the application belongs to the same customer
            self._check_application_customer(old_instance)

        # If the lease is associated with an section, we don not need to check for
        # other existing leases, since the section can have many active leases at the same time.
        if not self.section:
            existing_leases = WinterStorageLease.objects.filter(
                place=self.place,
                end_date__gt=self.start_date,
                status__in=ACTIVE_LEASE_STATUSES,
            ).exclude(pk=self.pk or None)
            if existing_leases.exists():
                raise ValidationError(_("WinterStoragePlace already has a lease"))
        if creating and self.place and not self.place.is_active:
            raise ValidationError(_("Selected place is not active"))

        super().clean()

    def _check_lease_place(self, old_instance) -> None:
        if self.place and self.place != old_instance.place:
            raise ValidationError(_("Cannot change the place assigned to this lease"))
        elif self.section and self.section != old_instance.section:
            raise ValidationError(_("Cannot change the section assigned to this lease"))

    def _check_application_customer(self, old_instance) -> None:
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

    def __str__(self):
        return " {} > {} - {} ({})".format(
            self.place or self.section, self.start_date, self.end_date, self.status
        )


class AbstractLeaseChange(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("time created"))
    from_status = models.CharField(
        choices=LeaseStatus.choices, verbose_name=_("from status"), max_length=30
    )
    to_status = models.CharField(
        choices=LeaseStatus.choices, verbose_name=_("to status"), max_length=30
    )

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
