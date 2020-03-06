import pytest  # noqa
from django.core.files.uploadedfile import SimpleUploadedFile

from resources.models import (
    get_harbor_media_folder,
    get_winter_area_media_folder,
    HarborMap,
    WinterStorageAreaMap,
)


def test_harbor_map_file_path(harbor):
    # Test that the proper path is set for the HarborMap file
    file = SimpleUploadedFile(
        name="map.pdf", content=None, content_type="application/pdf"
    )
    harbor_map = HarborMap.objects.create(map_file=file, harbor=harbor)
    assert get_harbor_media_folder(harbor_map, file) in harbor_map.map_file.path
    assert HarborMap.objects.count() == 1


def test_winter_storage_area_map_file_path(winter_storage_area):
    # Test that the proper path is set for the WinterStorageAreaMap file
    file = SimpleUploadedFile(
        name="map.pdf", content=None, content_type="application/pdf"
    )
    winter_storage_area_map = WinterStorageAreaMap.objects.create(
        map_file=file, winter_storage_area=winter_storage_area
    )
    assert (
        get_winter_area_media_folder(winter_storage_area_map, file)
        in winter_storage_area_map.map_file.path
    )
    assert WinterStorageAreaMap.objects.count() == 1
