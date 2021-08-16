from datetime import date

from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Exists, ExpressionWrapper, OuterRef, Q, QuerySet
from django.utils.translation import gettext_lazy as _
from helsinki_gdpr.models import SerializableMixin

from applications.models import BerthApplication, WinterStorageApplication
from customers.models import Boat, CustomerProfile
from payments.enums import OrderType
from resources.models import Berth, WinterStoragePlace, WinterStorageSection
from utils.models import TimeStampedModel, UUIDModel

from .consts import ACTIVE_LEASE_STATUSES
from .enums import LeaseStatus
from .utils import (
    calculate_berth_lease_end_date,
    calculate_berth_lease_start_date,
    calculate_season_start_date,
    calculate_winter_season_end_date,
    calculate_winter_season_start_date,
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
    orders = GenericRelation(
        "payments.Order",
        object_id_field="_lease_object_id",
        content_type_field="_lease_content_type",
    )

    comment = models.TextField(verbose_name=_("comment"), blank=True)

    class Meta:
        abstract = True

    @property
    def order(self):
        return self.orders.filter(order_type=OrderType.LEASE_ORDER).first()

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


class BerthLeaseManager(SerializableMixin.SerializableManager):
    def get_queryset(self):
        current_season_start = calculate_berth_lease_start_date()
        today = date.today()

        active_current_status = Q(status__in=ACTIVE_LEASE_STATUSES)

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

    def get_renewable_leases(self, season_start: date = None) -> QuerySet:
        """
        Get the leases that were active last year
        If today is:
          (1) before season: leases from last year
          (2) during or after season: leases from this year
        """
        qs = self.get_queryset()

        # Default the season start to the default season start date
        if not season_start:
            season_start = calculate_season_start_date()

        current_date = today().date()
        # If today is before the season starts but during the same year (1)
        if current_date < season_start and current_date.year == season_start.year:
            lease_year = current_date.year - 1
        else:  # (2)
            lease_year = current_date.year

        # Filter leases from the upcoming season
        future_leases = qs.filter(
            start_date__year__gt=lease_year,
            berth=OuterRef("berth"),
            customer=OuterRef("customer"),
        )

        # Exclude leases that have already been assigned to the same customer and berth on the future
        leases: QuerySet = qs.exclude(Exists(future_leases.values("pk"))).filter(
            # Only allow leases that are auto-renewing and have been paid
            berth__is_active=True,
            berth__is_invoiceable=True,
            status=LeaseStatus.PAID,
            start_date__year=lease_year,
            end_date__year=lease_year,
            contract__isnull=False,
        )

        return leases


class BerthLease(AbstractLease, SerializableMixin):
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
            end_date__gt=self.start_date,
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

    serialize_fields = (
        {"name": "id"},
        {"name": "boat", "accessor": lambda x: x.id if x else None},
        {"name": "status", "accessor": lambda x: dict(LeaseStatus.choices)[x]},
        {
            "name": "orders",
            "accessor": lambda orders: [order.id for order in orders.all()]
            if orders
            else None,
        },
        {"name": "comment"},
        {"name": "berth", "accessor": lambda x: x.serialize()},
        {"name": "application", "accessor": lambda x: x.id if x else None},
        {"name": "start_date", "accessor": lambda x: x.strftime("%d-%m-%Y")},
        {"name": "end_date", "accessor": lambda x: x.strftime("%d-%m-%Y")},
    )


class WinterStorageLeaseManager(SerializableMixin.SerializableManager):
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

    def get_renewable_marked_leases(self, season_start: date = None) -> QuerySet:
        """
        Get the leases that were active last last season
        If today is:
            (1) during the season: leases that start on the season's start year
            (2) outside of the season: leases that start on season's previous year
        """
        qs = self.get_queryset()

        # Default the season start to the default season start date
        if not season_start:
            season_start = calculate_winter_season_start_date()

        season_end = calculate_winter_season_end_date(season_start)
        current_date = today().date()

        # (1) If the season is ongoing:
        if season_start <= current_date < season_end:
            start_year = season_start.year
            end_year = season_start.year + 1
        # (2) if the season is not going on:
        else:
            start_year = season_start.year - 1
            end_year = season_start.year

        # Filter leases from the upcoming season
        future_leases = qs.filter(
            start_date__year__gte=end_year,
            place=OuterRef("place"),
            customer=OuterRef("customer"),
        )

        # Exclude leases that have already been assigned to the same customer and berth on the future
        leases: QuerySet = qs.exclude(Exists(future_leases.values("pk"))).filter(
            # Only allow leases that have been paid
            place__isnull=False,
            place__is_active=True,
            place__is_invoiceable=True,
            section__isnull=True,
            status=LeaseStatus.PAID,
            start_date__year=start_year,
            end_date__year=end_year,
        )

        return leases


class WinterStorageLease(AbstractLease, SerializableMixin):
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
    sticker_posted = models.DateField(
        verbose_name=_("sticker posted"), null=True, blank=True
    )
    objects = WinterStorageLeaseManager()

    class Meta:
        verbose_name = _("winter storage lease")
        verbose_name_plural = _("winter storage leases")
        default_related_name = "winter_storage_leases"

    def get_winter_storage_area(self):
        if self.place:
            return self.place.winter_storage_section.area
        elif self.section:
            return self.section.area
        else:
            raise Exception(f"WinterStorageLease {self} has no place or section")

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

    serialize_fields = (
        {"name": "id"},
        {"name": "boat", "accessor": lambda x: x.id if x else None},
        {"name": "status", "accessor": lambda x: dict(LeaseStatus.choices)[x]},
        {
            "name": "orders",
            "accessor": lambda orders: [order.id for order in orders.all()]
            if orders
            else None,
        },
        {"name": "comment"},
        {"name": "place", "accessor": lambda x: x.serialize() if x else None},
        {"name": "section", "accessor": lambda x: x.serialize() if x else None},
        {"name": "application", "accessor": lambda x: x.id if x else None},
        {"name": "start_date", "accessor": lambda x: x.strftime("%d-%m-%Y")},
        {"name": "end_date", "accessor": lambda x: x.strftime("%d-%m-%Y")},
        {"name": "sticker_number"},
        {
            "name": "sticker_posted",
            "accessor": lambda x: x.strftime("%d-%m-%Y") if x else None,
        },
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
