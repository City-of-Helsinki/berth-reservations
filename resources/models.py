from django.conf import settings
from django.contrib.gis.db import models
from django.core.files.storage import FileSystemStorage
from django.utils.translation import ugettext_lazy as _
from enumfields import EnumIntegerField
from munigeo.models import Municipality
from parler.models import TranslatableModel, TranslatedFields

from utils.models import UUIDModel

from .enums import BerthMooringType


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


class AbstractArea(UUIDModel):
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

    image_link = models.URLField(
        verbose_name=_("image link"), max_length=400, blank=True
    )

    class Meta:
        abstract = True


class Harbor(AbstractArea, TranslatableModel):
    municipality = models.ForeignKey(
        Municipality,
        null=True,
        blank=True,
        verbose_name=_("municipality"),
        related_name="harbors",
        on_delete=models.SET_NULL,
    )

    image_file = models.ImageField(
        upload_to=get_harbor_media_folder,
        storage=FileSystemStorage(),
        verbose_name=_("image file"),
        null=True,
        blank=True,
    )

    availability_level = models.ForeignKey(
        AvailabilityLevel,
        null=True,
        blank=True,
        verbose_name=_("availability level"),
        related_name="harbors",
        on_delete=models.SET_NULL,
    )

    number_of_places = models.PositiveSmallIntegerField(
        verbose_name=_("number of places"), null=True, blank=True
    )
    maximum_width = models.PositiveSmallIntegerField(
        verbose_name=_("maximum berth width"), null=True, blank=True
    )
    maximum_length = models.PositiveSmallIntegerField(
        verbose_name=_("maximum berth length"), null=True, blank=True
    )
    maximum_depth = models.PositiveSmallIntegerField(
        verbose_name=_("maximum berth depth"), null=True, blank=True
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

    image_file = models.ImageField(
        upload_to=get_winter_area_media_folder,
        storage=FileSystemStorage(),
        verbose_name=_("image file"),
        null=True,
        blank=True,
    )

    availability_level = models.ForeignKey(
        AvailabilityLevel,
        null=True,
        blank=True,
        verbose_name=_("availability level"),
        related_name="winter_storage_areas",
        on_delete=models.SET_NULL,
    )

    # Ruutupaikat (~ appointed marked places)
    # We can see in advance who gets a place and who does not.
    # We know their lengths and widths.
    number_of_marked_places = models.PositiveSmallIntegerField(
        verbose_name=_("number of marked places"), null=True, blank=True
    )
    max_width = models.PositiveSmallIntegerField(
        verbose_name=_("maximum place width"), null=True, blank=True
    )
    max_length = models.PositiveSmallIntegerField(
        verbose_name=_("maximum place length"), null=True, blank=True
    )

    # Lohkopaikat (~ section places)
    # People just queue for these, then as long as there s still space
    # next person in the queue can put his/her boat there.
    # The area is separated into sections, that limit the length of the suitable boat.
    number_of_section_spaces = models.PositiveSmallIntegerField(
        verbose_name=_("number of section places"), null=True, blank=True
    )
    max_length_of_section_spaces = models.PositiveSmallIntegerField(
        verbose_name=_("xaximum length of section spaces"), null=True, blank=True
    )

    # Nostojärjestyspaikat (~ unmarked places)
    # Same queing algorithm as with lohkopaikat.
    # No data of the dimensions.
    number_of_unmarked_spaces = models.PositiveSmallIntegerField(
        verbose_name=_("number of unmarked places"), null=True, blank=True
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


class AbstractAreaSection(UUIDModel):
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

    # TODO: make services as m2m field, when we have more specs?
    # Common services
    electricity = models.BooleanField(verbose_name=_("electricity"), default=False)
    water = models.BooleanField(verbose_name=_("water"), default=False)
    gate = models.BooleanField(verbose_name=_("gate"), default=False)

    class Meta:
        abstract = True


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

    class Meta:
        verbose_name = _("pier")
        verbose_name_plural = _("piers")
        ordering = ("harbor", "identifier")
        unique_together = (("identifier", "harbor"),)

    def __str__(self):
        if self.identifier:
            return "{} ({})".format(self.harbor, self.identifier)
        return self.harbor


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

    class Meta:
        verbose_name = _("winter storage section")
        verbose_name_plural = _("winter storage sections")
        ordering = ("area", "identifier")
        unique_together = (("area", "identifier"),)

    def __str__(self):
        if self.identifier:
            return "{} ({})".format(self.area, self.identifier)
        return self.area


class AbstractPlaceType(UUIDModel):
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
    mooring_type = EnumIntegerField(BerthMooringType, verbose_name=_("mooring type"))
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
        unique_together = (("width", "length", "mooring_type"),)

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


class AbstractBoatPlace(UUIDModel):
    number = models.CharField(verbose_name=_("number"), max_length=10)

    class Meta:
        abstract = True


class Berth(AbstractBoatPlace):
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

    class Meta:
        verbose_name = _("berth")
        verbose_name_plural = _("berths")
        ordering = ("pier", "number")
        unique_together = (("pier", "number"),)

    def __str__(self):
        return "{}: {}".format(self.pier, self.number)


class WinterStoragePlace(AbstractBoatPlace):
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

    class Meta:
        verbose_name = _("winter storage place")
        verbose_name_plural = _("winter storage places")
        ordering = ("winter_storage_section", "number")
        unique_together = (("winter_storage_section", "number"),)

    def __str__(self):
        return "{}: {}".format(self.winter_storage_section, self.number)
