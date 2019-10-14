from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.translation import activate
from parler.utils.context import switch_language

from harbors.models import WinterStorageArea as OldWinterArea
from resources.models import (
    WinterStorageArea,
    WinterStoragePlace,
    WinterStoragePlaceType,
    WinterStorageSection,
)

WINTER_AREAS_MAP = {
    # TODO: update temporary values here
    # from_place_number, to_place_number are just in basic order,
    # modify these numbers when more we have more specs
    "Iso-Sarvasto": [
        ((1, 29), 250, 600),  # ((from_place_number, to_place_number), width, length)
        ((30, 69), 300, 800),
        ((70, 85), 350, 1000),
        ((86, 89), 450, 1200),
    ],
    "Laivalahti": [
        ((1, 43), 250, 600),
        ((44, 68), 300, 800),
        ((69, 88), 350, 1000),
        ((89, 100), 450, 1200),
    ],
    "Porslahti": [((1, 21), 250, 600), ((22, 57), 300, 1000)],
    "Rajasaari": [
        ((1, 65), 240, 600),
        ((66, 135), 250, 600),
        ((136, 230), 300, 1000),
        ((231, 253), 400, 2000),
    ],
}


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.number_of_created_places = 0
        self.number_of_modified_places = 0
        self.missing_old_areas = []

    def handle(self, **options):

        for area_name, places_data in WINTER_AREAS_MAP.items():
            activate("fi")

            with transaction.atomic():
                area = WinterStorageArea.objects.translated(name=area_name).first()

                old_area = OldWinterArea.objects.translated(name=area_name).first()

                if old_area:
                    if not area:
                        area = WinterStorageArea.objects.create(
                            # default zip_code, field is non-nullable and non-blankable
                            zip_code="00100"
                        )

                    self._import_area_data_from_old_area(area, old_area)
                    self._import_section_data_from_old_area(area, old_area, places_data)

                else:
                    self.missing_old_areas.append(area_name)

        self.stdout.write(
            "Created {} winter storage places".format(self.number_of_created_places)
        )
        self.stdout.write(
            "Modified {} winter storage places".format(self.number_of_modified_places)
        )

        if self.missing_old_areas:
            self.stderr.write(
                "Following names had no existing winter areas: {}".format(
                    ", ".join(self.missing_old_areas)
                )
            )

    @staticmethod
    def _import_area_data_from_old_area(area, old_area):
        area.zip_code = old_area.zip_code
        area.phone = old_area.phone
        area.email = old_area.email
        area.www_url = old_area.www_url
        area.location = old_area.location
        area.municipality = old_area.municipality
        area.image_link = old_area.image_link

        for lang, _ in settings.LANGUAGES:
            with switch_language(area, lang):
                area.name = old_area.safe_translation_getter("name", language_code=lang)
                area.street_address = old_area.safe_translation_getter(
                    "street_address", language_code=lang
                )
                area.save()

    def _import_section_data_from_old_area(self, area, old_area, places_data):
        section, _ = WinterStorageSection.objects.get_or_create(
            area=area, identifier="-"
        )
        section.location = area.location
        section.electricity = old_area.electricity
        section.water = old_area.water
        section.gate = old_area.gate
        section.repair_area = old_area.repair_area
        section.summer_storage_for_docking_equipment = (
            old_area.summer_storage_for_docking_equipment
        )
        section.summer_storage_for_trailers = old_area.summer_storage_for_trailers
        section.summer_storage_for_boats = old_area.summer_storage_for_boats
        section.save()

        self._import_places(section, places_data)

    def _import_places(self, section, places_data):
        for places_type in places_data:
            place_nums, width, length = places_type
            from_place_num, to_place_num = place_nums

            for place_number in range(from_place_num, to_place_num + 1):
                place_number_str = str(place_number)
                if len(place_number_str) == 1:
                    # prepend 0 to number before 10
                    place_number_str = str(place_number).zfill(2)

                place_type, _ = WinterStoragePlaceType.objects.get_or_create(
                    width=width, length=length
                )

                _, created = WinterStoragePlace.objects.update_or_create(
                    winter_storage_section=section,
                    number=place_number_str,
                    defaults={"place_type": place_type},
                )
                if created:
                    self.number_of_created_places += 1
                else:
                    self.number_of_modified_places += 1