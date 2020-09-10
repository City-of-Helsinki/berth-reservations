import pytest  # noqa
from django.core.management import call_command
from munigeo.models import Municipality

from ..management.commands.generate_winter_places import WINTER_AREAS_MAP
from ..models import WinterStorageArea, WinterStoragePlace, WinterStorageSection


def test_generate_winter_places():
    # Helsinki municipalities required for the WSAreas
    Municipality.objects.create(id="helsinki")
    Municipality.objects.create(id="kirkkonummi")
    # Old WSAreas are required
    call_command("loaddata", "helsinki-winter-areas")
    call_command("generate_winter_places")
    for area_name, values in WINTER_AREAS_MAP.items():
        area = WinterStorageArea.objects.translated(name=area_name).first()
        assert area is not None

        for section_data in values:
            (
                section_identifier,
                (from_place_num, to_place_num),
                width,
                length,
            ) = section_data

            section = WinterStorageSection.objects.filter(
                area=area, identifier=section_identifier
            ).first()
            assert section is not None

            places = WinterStoragePlace.objects.filter(
                number__in=range(from_place_num, to_place_num + 1),
                winter_storage_section=section,
                place_type__width=width,
                place_type__length=length,
            ).count()
            assert places == (to_place_num - from_place_num) + 1
