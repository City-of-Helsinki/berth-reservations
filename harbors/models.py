import os
import shutil

from django.conf import settings
from django.contrib.gis.db import models
from django.core.files.storage import FileSystemStorage
from django.utils.translation import ugettext_lazy as _
from munigeo.models import Municipality
from parler.models import TranslatableModel, TranslatedFields


class BoatType(TranslatableModel):
    identifier = models.CharField(verbose_name=_('Unique identifier'), max_length=100, unique=True)
    translations = TranslatedFields(
        name=models.CharField(
            verbose_name=_('name'), max_length=200, help_text=_('Name of the boat type')
        ),
    )

    class Meta:
        verbose_name = _('boat type')
        verbose_name_plural = _('boat types')
        ordering = ('id',)

    def __str__(self):
        return "{} ({})".format(self.safe_translation_getter('name'), self.identifier)


def get_harbor_media_folder(instance, filename):
    return 'harbors/{harbor_identifier}/{filename}'.format(
        harbor_identifier=instance.identifier, filename=filename
    )


class OverwriteStorage(FileSystemStorage):
    """
    Custom storage that deletes previous harbor images
    by deleting the /harbors/{harbor_identifier}/ folder
    """

    def get_available_name(self, name, max_length=None):
        dir_name, file_name = os.path.split(name)
        if self.exists(dir_name):
            shutil.rmtree(os.path.join(settings.MEDIA_ROOT, dir_name))
        return name


class AvailabilityLevel(TranslatableModel):
    identifier = models.CharField(verbose_name=_('Unique identifier'), max_length=100, unique=True)
    translations = TranslatedFields(
        title=models.CharField(
            verbose_name=_('title'), max_length=64, blank=True,
            help_text=_('Title of the availability level'),
        ),
        description=models.TextField(
            verbose_name=_('description'), max_length=200, blank=True,
            help_text=_('Description of the availability level')
        ),
    )

    class Meta:
        verbose_name = _('availability level')
        verbose_name_plural = _('availability levels')
        ordering = ('id',)

    def __str__(self):
        return self.identifier


class Harbor(TranslatableModel):
    identifier = models.CharField(
        verbose_name=_('Unique identifier'), max_length=100, unique=True,
        help_text=_('Unique string to identify the harbor, e.g. `elaintarhanlahti` for Eläintarhanlahti')
    )

    # For importing coordinates and address from servicemap.hel.fi
    servicemap_id = models.CharField(
        verbose_name=_('Servicemap ID'), max_length=10, help_text=_('ID in the Servicemap system'),
        blank=True, null=True
    )

    zip_code = models.CharField(verbose_name=_('Postal code'), max_length=10, null=True, blank=True)
    phone = models.CharField(verbose_name=_('Phone number'), max_length=30, null=True, blank=True)
    email = models.EmailField(verbose_name=_('Email'), max_length=100, null=True, blank=True)
    www_url = models.URLField(verbose_name=_('WWW link'), max_length=400, null=True, blank=True)

    location = models.PointField(verbose_name=_('Location'), blank=True, null=True, srid=settings.DEFAULT_SRID)

    municipality = models.ForeignKey(
        Municipality, null=True, blank=True, verbose_name=_('Municipality'),
        related_name='harbors', on_delete=models.SET_NULL
    )

    image_file = models.ImageField(
        upload_to=get_harbor_media_folder, storage=OverwriteStorage(),
        verbose_name=_('Image file'), null=True, blank=True
    )
    image_link = models.URLField(verbose_name=_('Image link'), max_length=400, null=True, blank=True)

    # Available services
    mooring = models.BooleanField(verbose_name=_('Mooring'), default=False)
    electricity = models.BooleanField(verbose_name=_('Electricity'), default=False)
    water = models.BooleanField(verbose_name=_('Water'), default=False)
    waste_collection = models.BooleanField(verbose_name=_('Waste collection'), default=False)
    gate = models.BooleanField(verbose_name=_('Gate'), default=False)
    lighting = models.BooleanField(verbose_name=_('Lighting'), default=False)

    suitable_boat_types = models.ManyToManyField(
        BoatType, verbose_name=_('Suitable boat types'), related_name='harbors', blank=True
    )

    availability_level = models.ForeignKey(
        AvailabilityLevel, null=True, blank=True, verbose_name=_('Availability level'),
        related_name='harbors', on_delete=models.SET_NULL
    )

    number_of_places = models.PositiveSmallIntegerField(verbose_name=_('Number of places'), null=True, blank=True)
    maximum_width = models.PositiveSmallIntegerField(verbose_name=_('Maximum berth width'), null=True, blank=True)
    maximum_length = models.PositiveSmallIntegerField(verbose_name=_('Maximum berth length'), null=True, blank=True)
    maximum_depth = models.PositiveSmallIntegerField(verbose_name=_('Maximum berth depth'), null=True, blank=True)

    translations = TranslatedFields(
        name=models.CharField(
            verbose_name=_('name'), max_length=200, help_text=_('Name of the harbor'), blank=True
        ),
        street_address=models.CharField(
            verbose_name=_('street address'), max_length=200, help_text=_('Street address of the harbor'), blank=True
        ),
    )

    class Meta:
        verbose_name = _('harbor')
        verbose_name_plural = _('harbors')
        ordering = ('id',)

    def __str__(self):
        return "{} ({})".format(self.safe_translation_getter('name'), self.identifier)
