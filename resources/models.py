from dateutil.utils import today
from django.conf import settings
from django.contrib.gis.db import models
from django.contrib.postgres.aggregates import BoolOr
from django.core.files.storage import FileSystemStorage
from django.db.models import (
    BooleanField,
    Count,
    DecimalField,
    Exists,
    Max,
    OuterRef,
    PositiveIntegerField,
    Q,
    SmallIntegerField,
    Subquery,
    Sum,
    UniqueConstraint,
    Value,
)
from django.db.models.expressions import ExpressionWrapper, RawSQL
from django.db.models.functions import Coalesce
from django.utils.translation import gettext_lazy as _
from munigeo.models import Municipality
from parler.managers import TranslatableManager
from parler.models import TranslatableModel, TranslatedFields

from leases.consts import ACTIVE_LEASE_STATUSES
from leases.enums import LeaseStatus
from leases.utils import (
    calculate_berth_lease_end_date,
    calculate_berth_lease_start_date,
    calculate_winter_storage_lease_end_date,
)
from payments.enums import OfferStatus, PriceTier
from utils.models import TimeStampedModel, UUIDModel

from .enums import AreaRegion, BerthMooringType


class BoatType(TranslatableModel):
    translations = TranslatedFields(
        name=models.CharField(
            verbose_name=_("name"), max_length=200, help_text=_("Name of the boat type")
        )
    )

    class Meta:
        verbose_name = _("boat type")
        verbose_name_plural = _("boat types")
        ordering = ("id",)

    def __str__(self):
        return self.safe_translation_getter("name", super().__str__())


def get_harbor_media_folder(instance, filename):
    return "harbors/{harbor_id}/{filename}".format(
        harbor_id=instance.id, filename=filename
    )


def get_winter_area_media_folder(instance, filename):
    return "winter_areas/{area_id}/{filename}".format(
        area_id=instance.id, filename=filename
    )


def get_map_resource_media_folder(instance, filename):
    if isinstance(instance, HarborMap):
        return get_harbor_media_folder(instance.harbor, filename)
    elif isinstance(instance, WinterStorageAreaMap):
        return get_winter_area_media_folder(instance.winter_storage_area, filename)
    return None


class AvailabilityLevel(TranslatableModel):
    translations = TranslatedFields(
        title=models.CharField(
            verbose_name=_("title"),
            max_length=64,
            blank=True,
            help_text=_("Title of the availability level"),
        ),
        description=models.TextField(
            verbose_name=_("description"),
            max_length=200,
            blank=True,
            help_text=_("Description of the availability level"),
        ),
    )

    class Meta:
        verbose_name = _("availability level")
        verbose_name_plural = _("availability levels")
        ordering = ("id",)

    def __str__(self):
        return self.safe_translation_getter("title", super().__str__())


class AbstractArea(TimeStampedModel, UUIDModel):
    # For importing coordinates and address from servicemap.hel.fi
    servicemap_id = models.CharField(
        verbose_name=_("servicemap ID"),
        max_length=10,
        help_text=_("ID in the Servicemap system"),
        blank=True,
        null=True,
        unique=True,
    )

    zip_code = models.CharField(verbose_name=_("postal code"), max_length=10)
    phone = models.CharField(verbose_name=_("phone number"), max_length=30, blank=True)
    email = models.EmailField(verbose_name=_("email"), max_length=100, blank=True)
    www_url = models.URLField(verbose_name=_("WWW link"), max_length=400, blank=True)

    location = models.PointField(
        verbose_name=_("location"), blank=True, null=True, srid=settings.DEFAULT_SRID
    )

    image_file = models.CharField(
        verbose_name=_("Image file"), max_length=400, null=True, blank=True
    )
    region = models.CharField(
        choices=AreaRegion.choices,
        verbose_name=_("area region"),
        max_length=32,
        blank=True,
        null=True,
    )

    @property
    def image_file_url(self) -> str:
        return settings.VENE_UI_URL + self.image_file if self.image_file else None

    class Meta:
        abstract = True


class HarborManager(TranslatableManager):
    def get_queryset(self):
        pier_qs = Pier.objects.filter(harbor=OuterRef("pk")).values("harbor__pk")
        width_qs = pier_qs.annotate(max=Max("max_width")).values("max")
        length_qs = pier_qs.annotate(max=Max("max_length")).values("max")
        depth_qs = pier_qs.annotate(max=Max("max_depth")).values("max")
        number_of_free_places_qs = pier_qs.annotate(
            count=Sum("number_of_free_places")
        ).values("count")
        number_of_inactive_places_qs = pier_qs.annotate(
            count=Sum("number_of_inactive_places")
        ).values("count")
        number_of_places_qs = pier_qs.annotate(count=Sum("number_of_places")).values(
            "count"
        )

        return (
            super()
            .get_queryset()
            .annotate(
                max_width=Subquery(width_qs, output_field=DecimalField()),
                max_length=Subquery(length_qs, output_field=DecimalField()),
                max_depth=Subquery(depth_qs, output_field=DecimalField()),
                number_of_free_places=Subquery(
                    number_of_free_places_qs, output_field=SmallIntegerField()
                ),
                number_of_inactive_places=Subquery(
                    number_of_inactive_places_qs, output_field=SmallIntegerField()
                ),
                number_of_places=Subquery(
                    number_of_places_qs, output_field=SmallIntegerField()
                ),
                electricity=BoolOr("piers__electricity"),
                water=BoolOr("piers__water"),
                gate=BoolOr("piers__gate"),
                mooring=BoolOr("piers__mooring"),
                waste_collection=BoolOr("piers__waste_collection"),
                lighting=BoolOr("piers__lighting"),
            )
        )


class Harbor(AbstractArea, TranslatableModel):
    municipality = models.ForeignKey(
        Municipality,
        null=True,
        blank=True,
        verbose_name=_("municipality"),
        related_name="harbors",
        on_delete=models.SET_NULL,
    )
    availability_level = models.ForeignKey(
        AvailabilityLevel,
        null=True,
        blank=True,
        verbose_name=_("availability level"),
        related_name="harbors",
        on_delete=models.SET_NULL,
    )

    translations = TranslatedFields(
        name=models.CharField(
            verbose_name=_("name"),
            max_length=200,
            help_text=_("Name of the harbor"),
            blank=True,
        ),
        street_address=models.CharField(
            verbose_name=_("street address"),
            max_length=200,
            help_text=_("Street address of the harbor"),
            blank=True,
        ),
    )

    objects = HarborManager()

    class Meta:
        verbose_name = _("harbor")
        verbose_name_plural = _("harbors")

    def __str__(self):
        return self.safe_translation_getter("name", super().__str__())


class WinterStorageArea(AbstractArea, TranslatableModel):
    municipality = models.ForeignKey(
        Municipality,
        null=True,
        blank=True,
        verbose_name=_("municipality"),
        related_name="winter_storage_areas",
        on_delete=models.SET_NULL,
    )
    availability_level = models.ForeignKey(
        AvailabilityLevel,
        null=True,
        blank=True,
        verbose_name=_("availability level"),
        related_name="winter_storage_areas",
        on_delete=models.SET_NULL,
    )

    # Lohkopaikat (~ section places)
    # People just queue for these, then as long as there s still space
    # next person in the queue can put his/her boat there.
    # The area is separated into sections, that limit the length of the suitable boat.
    estimated_number_of_section_spaces = models.PositiveSmallIntegerField(
        verbose_name=_("estimated number of section places"), null=True, blank=True
    )
    max_length_of_section_spaces = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name=_("maximum length of section spaces"),
        null=True,
        blank=True,
    )

    # Nostojärjestyspaikat (~ unmarked places)
    # Same queing algorithm as with lohkopaikat.
    # No data of the dimensions.
    estimated_number_of_unmarked_spaces = models.PositiveSmallIntegerField(
        verbose_name=_("estimated number of unmarked places"), null=True, blank=True
    )

    translations = TranslatedFields(
        name=models.CharField(
            verbose_name=_("name"),
            max_length=200,
            help_text=_("Name of the area"),
            blank=True,
        ),
        street_address=models.CharField(
            verbose_name=_("street address"),
            max_length=200,
            help_text=_("Street address of the area"),
            blank=True,
        ),
    )

    class Meta:
        verbose_name = _("winter storage area")
        verbose_name_plural = _("winter storage areas")

    def __str__(self):
        return self.safe_translation_getter("name", super().__str__())


class AbstractAreaMap(UUIDModel):
    map_file = models.FileField(
        upload_to=get_map_resource_media_folder,
        storage=FileSystemStorage(),
        verbose_name=_("map file"),
        null=False,
        blank=False,
    )

    class Meta:
        abstract = True


class HarborMap(AbstractAreaMap):
    harbor = models.ForeignKey(
        Harbor, verbose_name=_("harbor"), related_name="maps", on_delete=models.CASCADE,
    )


class WinterStorageAreaMap(AbstractAreaMap):
    winter_storage_area = models.ForeignKey(
        WinterStorageArea,
        verbose_name=_("winter storage area"),
        related_name="maps",
        on_delete=models.CASCADE,
    )


class AbstractAreaSection(TimeStampedModel, UUIDModel):
    """
    AreaSection models keep the information about the services
    available at this pier or winter storage section.

    If it is the only pier/section in the harbor/area,
    identifier field can be left blank.
    """

    identifier = models.CharField(
        verbose_name=_("identifier"),
        help_text=_("Identifier of the pier / section"),
        max_length=30,
        blank=True,
    )

    # More precise location of the specific piers / winter area sections
    location = models.PointField(
        verbose_name=_("location"), blank=True, null=True, srid=settings.DEFAULT_SRID
    )

    # Common services
    electricity = models.BooleanField(verbose_name=_("electricity"), default=False)
    water = models.BooleanField(verbose_name=_("water"), default=False)
    gate = models.BooleanField(verbose_name=_("gate"), default=False)

    class Meta:
        abstract = True


def _get_dimensions_qs(base_qs, place_type_name, section_name):
    def dimension_qs(dimension):
        return (
            base_qs.order_by()
            .values(section_name)
            .annotate(count=Max(f"{place_type_name}__{dimension}"))
            .values("count")
        )

    return dimension_qs


class PierManager(models.Manager):
    def get_queryset(self):
        berth_qs = Berth.objects.filter(pier=OuterRef("pk"))
        dimension_qs = _get_dimensions_qs(
            berth_qs, place_type_name="berth_type", section_name="pier"
        )

        # When annotating the count, if no elements match the filter, the whole queryset will
        # return an empty QuerySet<[]>, which will then return None as value for the count.
        #
        # By adding the other annotate with Coalesce, we ensure that, we'll always get an int value
        available_berths = (
            berth_qs.filter(is_available=True, is_active=True)
            .order_by()
            .values("pier")
            .annotate(nullable_count=Count("*"))
            .values("nullable_count")
            .annotate(count=Coalesce("nullable_count", Value(0)))
            .values("count")
        )
        inactive_berths = (
            berth_qs.filter(Q(is_active=False))
            .order_by()
            .values("pier")
            .annotate(nullable_count=Count("*"))
            .values("nullable_count")
            .annotate(count=Coalesce("nullable_count", Value(0)))
            .values("count")
        )

        all_berths = (
            berth_qs.order_by()
            .values("pier")
            .annotate(count=Count("*"))
            .values("count")
        )

        return (
            super()
            .get_queryset()
            .annotate(
                max_width=Subquery(dimension_qs("width"), output_field=DecimalField()),
                max_length=Subquery(
                    dimension_qs("length"), output_field=DecimalField()
                ),
                max_depth=Subquery(dimension_qs("depth"), output_field=DecimalField()),
                number_of_places=Subquery(
                    all_berths, output_field=PositiveIntegerField()
                ),
                number_of_free_places=Subquery(
                    available_berths, output_field=PositiveIntegerField()
                ),
                number_of_inactive_places=Subquery(
                    inactive_berths, output_field=PositiveIntegerField(),
                ),
            )
        )


class WinterStorageSectionManager(models.Manager):
    def get_queryset(self):
        place_qs = WinterStoragePlace.objects.filter(
            winter_storage_section=OuterRef("pk")
        )
        dimension_qs = _get_dimensions_qs(
            place_qs,
            place_type_name="place_type",
            section_name="winter_storage_section",
        )

        # When annotating the count, if no elements match the filter, the whole queryset will
        # return an empty QuerySet<[]>, which will then return None as value for the count.
        #
        # By adding the other annotate with Coalesce, we ensure that, we'll always get an int value
        available_places = (
            place_qs.filter(is_available=True, is_active=True)
            .order_by()
            .values("winter_storage_section")
            .annotate(nullable_count=Count("*"))
            .values("nullable_count")
            .annotate(count=Coalesce("nullable_count", Value(0)))
            .values("count")
        )
        inactive_places = (
            place_qs.filter(Q(is_active=False))
            .order_by()
            .values("winter_storage_section")
            .annotate(nullable_count=Count("*"))
            .values("nullable_count")
            .annotate(count=Coalesce("nullable_count", Value(0)))
            .values("count")
        )

        all_places = (
            place_qs.order_by()
            .values("winter_storage_section")
            .annotate(count=Count("*"))
            .values("count")
        )

        return (
            super()
            .get_queryset()
            .annotate(
                max_width=Subquery(dimension_qs("width"), output_field=DecimalField(),),
                max_length=Subquery(
                    dimension_qs("length"), output_field=DecimalField(),
                ),
                number_of_places=Subquery(
                    all_places, output_field=PositiveIntegerField()
                ),
                number_of_free_places=Subquery(
                    available_places, output_field=PositiveIntegerField()
                ),
                number_of_inactive_places=Subquery(
                    inactive_places, output_field=PositiveIntegerField(),
                ),
            )
        )


class Pier(AbstractAreaSection):
    harbor = models.ForeignKey(
        Harbor, verbose_name=_("harbor"), related_name="piers", on_delete=models.CASCADE
    )

    suitable_boat_types = models.ManyToManyField(
        BoatType,
        verbose_name=_("suitable boat types"),
        related_name="piers",
        blank=True,
    )

    # Additional harbor services
    mooring = models.BooleanField(verbose_name=_("mooring"), default=False)
    waste_collection = models.BooleanField(
        verbose_name=_("waste collection"), default=False
    )
    lighting = models.BooleanField(verbose_name=_("lighting"), default=False)
    personal_electricity = models.BooleanField(
        verbose_name=_("personal electricity contract"), default=False
    )
    price_tier = models.PositiveSmallIntegerField(
        choices=PriceTier.choices,
        verbose_name=_("price tier"),
        default=PriceTier.TIER_1,
    )
    harbors_harbor = models.ForeignKey(
        "harbors.Harbor",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="resources_pier",
    )

    objects = PierManager()

    class Meta:
        verbose_name = _("pier")
        verbose_name_plural = _("piers")
        ordering = ("harbor", "identifier")
        unique_together = (("identifier", "harbor"),)

    def __str__(self):
        return "{} ({})".format(self.harbor, self.identifier or "-")


class WinterStorageSection(AbstractAreaSection):
    area = models.ForeignKey(
        WinterStorageArea,
        verbose_name=_("winter storage area"),
        related_name="sections",
        on_delete=models.CASCADE,
    )

    # Additional winter storage area services
    repair_area = models.BooleanField(verbose_name=_("repair area"), default=False)
    summer_storage_for_docking_equipment = models.BooleanField(
        verbose_name=_("summer storage for docking equipment"), default=False
    )
    summer_storage_for_trailers = models.BooleanField(
        verbose_name=_("summer storage for trailers"), default=False
    )
    summer_storage_for_boats = models.BooleanField(
        verbose_name=_("summer storage for boats"), default=False
    )

    objects = WinterStorageSectionManager()

    class Meta:
        verbose_name = _("winter storage section")
        verbose_name_plural = _("winter storage sections")
        ordering = ("area", "identifier")
        unique_together = (("area", "identifier"),)

    def __str__(self):
        return "{} ({})".format(self.area, self.identifier or "-")


class AbstractPlaceType(TimeStampedModel, UUIDModel):
    """
    This model stores a combination of place's dimensions
       (and - for berths - its mooring type).

    It is needed for:
    - easier bulk management of places
        (e.g. changing some dimension on multiple places at once)
    - easier grouping of places into categories
        (e.g. for admins to see how many suitable places are there for a boat)
    """

    width = models.DecimalField(
        max_digits=5, decimal_places=2, verbose_name=_("width (m)")
    )
    length = models.DecimalField(
        max_digits=5, decimal_places=2, verbose_name=_("length (m)")
    )

    class Meta:
        abstract = True


class BerthType(AbstractPlaceType):
    mooring_type = models.PositiveSmallIntegerField(
        choices=BerthMooringType.choices, verbose_name=_("mooring type")
    )
    depth = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name=_("depth (m)"),
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = _("berth type")
        verbose_name_plural = _("berth types")
        ordering = ("width", "length", "depth")
        constraints = [
            UniqueConstraint(
                fields=("width", "length", "depth", "mooring_type"),
                name="unique_dimension",
            )
        ]

    def __str__(self):
        return "{} x {} - {}".format(self.width, self.length, str(self.mooring_type))


class WinterStoragePlaceType(AbstractPlaceType):
    class Meta:
        verbose_name = _("winter storage place type")
        verbose_name_plural = _("winter storage place types")
        ordering = ("width", "length")
        unique_together = (("width", "length"),)

    def __str__(self):
        return "{} x {}".format(self.width, self.length)


class AbstractBoatPlace(TimeStampedModel, UUIDModel):
    is_active = models.BooleanField(verbose_name=_("is active"), default=True)

    class Meta:
        abstract = True


class BerthManager(models.Manager):
    def get_queryset(self):
        """
        The QuerySet annotates whether a berth is available or not. For this,
        it considers the following criteria:
            - If there are leases associated to the berth
            - If any lease ends during the current or the last season (previous year)
                + If a lease ends during the current season:
                    * It needs to have a "valid" status (DRAFTED, OFFERED, PAID, ERROR)
                + If a lease ended during the last season:
                    * It should not have been renewed for the next season
                    * It needs to have a "valid" status (PAID)
        """
        from leases.models import BerthLease
        from payments.models import BerthSwitchOffer

        season_start = calculate_berth_lease_start_date()
        season_end = calculate_berth_lease_end_date()
        current_date = today().date()

        # If today is before the season ends but during the same year
        if current_date < season_end and current_date.year == season_end.year:
            last_year = current_date.year - 1
        else:
            last_year = current_date.year

        in_current_season = Q(
            # Check the lease starts at some point the during the season
            start_date__gte=season_start,
            # Check the lease ends earliest at the beginning of the season
            # (for leases terminated before the season started)
            end_date__gte=season_start,
            # Check the lease ends latest at the end of the season
            end_date__lte=season_end,
        )
        in_last_season = Q(end_date__year=last_year)

        active_current_status = Q(status__in=ACTIVE_LEASE_STATUSES)
        paid_status = Q(status=LeaseStatus.PAID)

        # In case the renewed leases for the upcoming season haven't been sent
        # or some of the leases that had to be fixed (also for the upcoming season)
        # are pending, we check for leases on the previous season that have already been paid,
        # which in most cases means that the customer will keep the berth for the next season as well.
        #
        # Pre-filter the leases for the upcoming/current season
        renewed_leases = BerthLease.objects.filter(
            in_current_season, berth=OuterRef("berth"), customer=OuterRef("customer"),
        ).values("pk")
        # Filter the leases from the previous season that have already been renewed
        previous_leases = (
            BerthLease.objects.exclude(Exists(renewed_leases))
            .filter(in_last_season, paid_status, berth=OuterRef("pk"))
            .values("pk")
        )

        # For the leases that have been renewed or are valid during the current season.
        # Filter the leases on the current season that have not been rejected
        current_leases = BerthLease.objects.filter(
            in_current_season, active_current_status, berth=OuterRef("pk")
        ).values("pk")

        # A berth is NOT available when it already has a lease on the current (or upcoming) season
        # or when the previous season lease has been paid and the new leases have not been sent.
        active_leases = ~Exists(previous_leases | current_leases)

        # Additionally, the berth is also NOT available when there is a switch offer drafted or offered
        # (this requires separate Exists clauses
        active_offers = ~Exists(
            BerthSwitchOffer.objects.filter(
                status__in=(OfferStatus.DRAFTED, OfferStatus.OFFERED),
                berth=OuterRef("pk"),
            ).values("pk")
        )

        # Need to explicitly mark the result of the AND as a BooleanField
        is_available = ExpressionWrapper(
            Q(active_leases & active_offers), output_field=BooleanField()
        )

        return (
            super()
            .get_queryset()
            .annotate(
                is_available=is_available,
                _int_number=RawSQL(
                    "CAST(substring(number FROM '^[0-9]+') AS INTEGER)",
                    params=[],
                    output_field=models.PositiveSmallIntegerField(),
                ),
            )
            .order_by("_int_number")
        )


class Berth(AbstractBoatPlace):
    number = models.CharField(verbose_name=_("number"), max_length=30)

    pier = models.ForeignKey(
        Pier, verbose_name=_("pier"), related_name="berths", on_delete=models.CASCADE
    )
    berth_type = models.ForeignKey(
        BerthType,
        verbose_name=_("berth type"),
        related_name="berths",
        on_delete=models.PROTECT,
    )
    comment = models.TextField(verbose_name=_("comment"), blank=True,)
    is_accessible = models.BooleanField(
        verbose_name=_("is accessible"), blank=True, null=True,
    )
    is_invoiceable = models.BooleanField(verbose_name=_("is invoiceable"), default=True)

    objects = BerthManager()

    class Meta:
        verbose_name = _("berth")
        verbose_name_plural = _("berths")
        ordering = ("pier",)
        unique_together = (("pier", "number"),)

    def __str__(self):
        return "{}: {}".format(self.pier, self.number)


class WinterStoragePlaceManager(models.Manager):
    def get_queryset(self):
        """
        The QuerySet annotates whether a place is available or not. For this,
        it considers the following criteria:
            - If there are leases associated to the  place
            - If any lease ends during the current or the last season (previous year)
                + If a lease ends during the current season:
                    * It needs to have a "valid" status (DRAFTED, OFFERED, PAID, ERROR)
                + If a lease ended during the last season:
                    * It should not have been renewed for the next season
                    * It needs to have a "valid" status (PAID)
        """
        from leases.models import WinterStorageLease

        season_end = calculate_winter_storage_lease_end_date()
        current_date = today().date()

        # If today is before the season ends but during the same year
        if current_date < season_end and current_date.year == season_end.year:
            last_year = current_date.year - 1
        else:
            last_year = current_date.year

        in_current_season = Q(end_date__gte=season_end)
        in_last_season = Q(end_date__year=last_year)

        active_current_status = Q(status__in=ACTIVE_LEASE_STATUSES)
        paid_status = Q(status=LeaseStatus.PAID)

        # In case the renewed leases for the upcoming season haven't been sent
        # or some of the leases that had to be fixed (also for the upcoming season)
        # are pending, we check for leases on the previous season that have already been paid,
        # which in most cases means that the customer will keep the berth for the next season as well.
        #
        # Pre-filter the leases for the upcoming/current season
        renewed_leases = WinterStorageLease.objects.filter(
            in_current_season, place=OuterRef("place"), customer=OuterRef("customer"),
        )
        # Filter the leases from the previous season that have already been renewed
        previous_leases = WinterStorageLease.objects.exclude(
            Exists(renewed_leases)
        ).filter(in_last_season, paid_status, place=OuterRef("pk"))

        # For the leases that have been renewed or are valid during the current season.
        # Filter the leases on the current season that have not been rejected
        current_leases = WinterStorageLease.objects.filter(
            in_current_season, active_current_status, place=OuterRef("pk")
        )

        # A berth is NOT available when it already has a lease on the current (or upcoming) season
        # or when the previous season lease has been paid and the new leases have not been sent
        is_available = ~Exists(previous_leases | current_leases)

        return super().get_queryset().annotate(is_available=is_available)


class WinterStoragePlace(AbstractBoatPlace):
    number = models.PositiveSmallIntegerField(verbose_name=_("number"))

    winter_storage_section = models.ForeignKey(
        WinterStorageSection,
        verbose_name=_("winter storage section"),
        related_name="places",
        on_delete=models.CASCADE,
    )
    place_type = models.ForeignKey(
        WinterStoragePlaceType,
        verbose_name=_("place type"),
        related_name="places",
        on_delete=models.PROTECT,
    )
    objects = WinterStoragePlaceManager()

    class Meta:
        verbose_name = _("winter storage place")
        verbose_name_plural = _("winter storage places")
        ordering = ("winter_storage_section", "number")
        unique_together = (("winter_storage_section", "number"),)

    def __str__(self):
        return "{}: {}".format(self.winter_storage_section, self.number)
