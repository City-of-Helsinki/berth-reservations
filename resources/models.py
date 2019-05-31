import os
import shutil

from django.conf import settings
from django.contrib.gis.db import models
from django.core.files.storage import FileSystemStorage
from django.utils.translation import ugettext_lazy as _
from munigeo.models import Municipality
from parler.models import TranslatableModel, TranslatedFields


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


class OverwriteStorage(FileSystemStorage):
    """
    Custom storage that deletes previous harbor images
    by deleting the /harbors/{harbor_id}/ folder
    """

    def get_available_name(self, name, max_length=None):
        dir_name, file_name = os.path.split(name)
        if self.exists(dir_name):
            shutil.rmtree(os.path.join(settings.MEDIA_ROOT, dir_name))
        return name


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


class AbstractArea(models.Model):
    # For importing coordinates and address from servicemap.hel.fi
    servicemap_id = models.CharField(
        verbose_name=_("servicemap ID"),
        max_length=10,
        help_text=_("ID in the Servicemap system"),
        blank=True,
        null=True,
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

    # Common services
    electricity = models.BooleanField(verbose_name=_("electricity"), default=False)
    water = models.BooleanField(verbose_name=_("water"), default=False)
    gate = models.BooleanField(verbose_name=_("gate"), default=False)

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
        storage=OverwriteStorage(),
        verbose_name=_("image file"),
        null=True,
        blank=True,
    )

    # Additional harbor services
    mooring = models.BooleanField(verbose_name=_("mooring"), default=False)
    waste_collection = models.BooleanField(
        verbose_name=_("waste collection"), default=False
    )
    lighting = models.BooleanField(verbose_name=_("lighting"), default=False)

    suitable_boat_types = models.ManyToManyField(
        BoatType,
        verbose_name=_("suitable boat types"),
        related_name="harbors",
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
        ordering = ("id",)

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
        storage=OverwriteStorage(),
        verbose_name=_("image file"),
        null=True,
        blank=True,
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
        ordering = ("id",)

    def __str__(self):
        return self.safe_translation_getter("name", super().__str__())
