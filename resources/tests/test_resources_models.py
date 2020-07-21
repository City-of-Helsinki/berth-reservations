import os
import random
from pathlib import Path

import pytest  # noqa
from django.core.files.uploadedfile import SimpleUploadedFile
from freezegun import freeze_time

from leases.enums import LeaseStatus
from leases.tests.factories import BerthLeaseFactory
from leases.utils import (
    calculate_berth_lease_end_date,
    calculate_berth_lease_start_date,
)
from payments.models import BerthPriceGroup
from payments.tests.factories import BerthPriceGroupFactory
from resources.models import (
    Berth,
    BerthType,
    get_harbor_media_folder,
    get_winter_area_media_folder,
    Harbor,
    HarborMap,
    Pier,
    WinterStorageArea,
    WinterStorageAreaMap,
)
from resources.tests.factories import BerthFactory, BerthTypeFactory, PierFactory


def test_harbor_map_file_path(harbor):
    # Test that the proper path is set for the HarborMap file
    file = SimpleUploadedFile(
        name="map.pdf", content=None, content_type="application/pdf"
    )
    harbor_map = HarborMap.objects.create(map_file=file, harbor=harbor)
    assert get_harbor_media_folder(harbor_map.harbor, file) in harbor_map.map_file.path
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
        get_winter_area_media_folder(winter_storage_area_map.winter_storage_area, file)
        in winter_storage_area_map.map_file.path
    )
    assert WinterStorageAreaMap.objects.count() == 1


def test_harbor_image_added():
    file_name = "image.png"
    harbor = Harbor.objects.create(
        image_file=SimpleUploadedFile(
            name=file_name, content=None, content_type="image/png"
        )
    )

    directory = Path(harbor.image_file.path).parent
    files = os.listdir(directory)

    # Test that the directory contains the image
    assert len(files) == 1
    assert files[0] == file_name


def test_harbor_image_removed():
    file_name = "image.png"
    harbor = Harbor.objects.create(
        image_file=SimpleUploadedFile(
            name=file_name, content=None, content_type="image/png"
        )
    )

    directory = Path(harbor.image_file.path).parent
    files = os.listdir(directory)

    # Test that the directory contains the image
    assert len(files) == 1
    assert files[0] == file_name

    harbor.image_file = None
    harbor.save()

    # Test that the image is being removed from the directory
    files = os.listdir(directory)
    assert len(files) == 0


def test_harbor_image_replaced():
    file_name_1 = "image1.png"
    file_name_2 = "image2.png"

    harbor = Harbor.objects.create(
        image_file=SimpleUploadedFile(
            name=file_name_1, content=None, content_type="image/png"
        )
    )

    directory = Path(harbor.image_file.path).parent
    files = os.listdir(directory)

    # Test that the directory contains the image
    assert len(files) == 1
    assert files[0] == file_name_1

    harbor.image_file = SimpleUploadedFile(
        name=file_name_2, content=None, content_type="image/png"
    )
    harbor.save()

    files = os.listdir(directory)
    # Test that the image is being removed from the directory
    assert len(files) == 1
    assert files[0] == file_name_2


def test_harbor_files_not_removed():
    image_file_name = "image1.png"
    map1_file_name = "map1.pdf"
    map2_file_name = "map2.pdf"

    harbor = Harbor.objects.create(
        image_file=SimpleUploadedFile(
            name=image_file_name, content=None, content_type="image/png"
        )
    )
    harbor_map1 = HarborMap.objects.create(
        map_file=SimpleUploadedFile(
            name=map1_file_name, content=None, content_type="application/pdf"
        ),
        harbor=harbor,
    )

    directory = Path(harbor_map1.map_file.path).parent

    # Check that the files are in the same directory
    assert Path(harbor_map1.map_file.path).parent == Path(harbor.image_file.path).parent

    files = os.listdir(directory)
    file_names = [image_file_name, map1_file_name]
    # Test that the directory contains the map and the image
    assert len(files) == 2
    assert all(file in files for file in file_names)

    HarborMap.objects.create(
        map_file=SimpleUploadedFile(
            name=map2_file_name, content=None, content_type="application/pdf"
        ),
        harbor=harbor,
    )

    files = list(os.listdir(directory))
    file_names.append(map2_file_name)
    # Test that the directory contains the map and the image
    assert len(files) == 3
    assert all(file in files for file in file_names)


def test_all_harbor_files_removed():
    image_file_name = "image1.png"
    map1_file_name = "map1.pdf"
    map2_file_name = "map2.pdf"

    harbor = Harbor.objects.create(
        image_file=SimpleUploadedFile(
            name=image_file_name, content=None, content_type="image/png"
        )
    )
    HarborMap.objects.create(
        map_file=SimpleUploadedFile(
            name=map1_file_name, content=None, content_type="application/pdf"
        ),
        harbor=harbor,
    )
    HarborMap.objects.create(
        map_file=SimpleUploadedFile(
            name=map2_file_name, content=None, content_type="application/pdf"
        ),
        harbor=harbor,
    )

    directory = Path(harbor.image_file.path).parent

    files = os.listdir(directory)
    file_names = [image_file_name, map1_file_name, map2_file_name]
    # Test that the directory contains the map and the image
    assert len(files) == 3
    assert all(file in files for file in file_names)

    harbor.delete()

    # Test that all the directory have been removed
    assert not directory.exists()


def test_winter_storage_area_image_added():
    file_name = "image.png"
    winter_storage_area = WinterStorageArea.objects.create(
        image_file=SimpleUploadedFile(
            name=file_name, content=None, content_type="image/png"
        )
    )

    directory = Path(winter_storage_area.image_file.path).parent
    files = os.listdir(directory)

    # Test that the directory contains the image
    assert len(files) == 1
    assert files[0] == file_name


def test_winter_storage_area_image_removed():
    file_name = "image.png"
    winter_storage_area = WinterStorageArea.objects.create(
        image_file=SimpleUploadedFile(
            name=file_name, content=None, content_type="image/png"
        )
    )

    directory = Path(winter_storage_area.image_file.path).parent
    files = os.listdir(directory)

    # Test that the directory contains the image
    assert len(files) == 1
    assert files[0] == file_name

    winter_storage_area.image_file = None
    winter_storage_area.save()

    # Test that the image is being removed from the directory
    files = os.listdir(directory)
    assert len(files) == 0


def test_winter_storage_area_image_replaced():
    file_name_1 = "image1.png"
    file_name_2 = "image2.png"

    winter_storage_area = WinterStorageArea.objects.create(
        image_file=SimpleUploadedFile(
            name=file_name_1, content=None, content_type="image/png"
        )
    )

    directory = Path(winter_storage_area.image_file.path).parent
    files = os.listdir(directory)

    # Test that the directory contains the image
    assert len(files) == 1
    assert files[0] == file_name_1

    winter_storage_area.image_file = SimpleUploadedFile(
        name=file_name_2, content=None, content_type="image/png"
    )
    winter_storage_area.save()

    files = os.listdir(directory)
    # Test that the image is being removed from the directory
    assert len(files) == 1
    assert files[0] == file_name_2


def test_winter_storage_area_files_not_removed():
    image_file_name = "image1.png"
    map1_file_name = "map1.pdf"
    map2_file_name = "map2.pdf"

    winter_storage_area = WinterStorageArea.objects.create(
        image_file=SimpleUploadedFile(
            name=image_file_name, content=None, content_type="image/png"
        )
    )
    winter_storage_area_map1 = WinterStorageAreaMap.objects.create(
        map_file=SimpleUploadedFile(
            name=map1_file_name, content=None, content_type="application/pdf"
        ),
        winter_storage_area=winter_storage_area,
    )

    directory = Path(winter_storage_area_map1.map_file.path).parent

    # Check that the files are in the same directory
    assert (
        Path(winter_storage_area_map1.map_file.path).parent
        == Path(winter_storage_area.image_file.path).parent
    )

    files = os.listdir(directory)
    file_names = [image_file_name, map1_file_name]
    # Test that the directory contains the map and the image
    assert len(files) == 2
    assert all(file in files for file in file_names)

    WinterStorageAreaMap.objects.create(
        map_file=SimpleUploadedFile(
            name=map2_file_name, content=None, content_type="application/pdf"
        ),
        winter_storage_area=winter_storage_area,
    )

    files = list(os.listdir(directory))
    file_names.append(map2_file_name)
    # Test that the directory contains the map and the image
    assert len(files) == 3
    assert all(file in files for file in file_names)


def test_all_winter_storage_area_files_removed():
    image_file_name = "image1.png"
    map1_file_name = "map1.pdf"
    map2_file_name = "map2.pdf"

    winter_storage_area = WinterStorageArea.objects.create(
        image_file=SimpleUploadedFile(
            name=image_file_name, content=None, content_type="image/png"
        )
    )
    WinterStorageAreaMap.objects.create(
        map_file=SimpleUploadedFile(
            name=map1_file_name, content=None, content_type="application/pdf"
        ),
        winter_storage_area=winter_storage_area,
    )
    WinterStorageAreaMap.objects.create(
        map_file=SimpleUploadedFile(
            name=map2_file_name, content=None, content_type="application/pdf"
        ),
        winter_storage_area=winter_storage_area,
    )

    directory = Path(winter_storage_area.image_file.path).parent

    files = os.listdir(directory)
    file_names = [image_file_name, map1_file_name, map2_file_name]
    # Test that the directory contains the map and the image
    assert len(files) == 3
    assert all(file in files for file in file_names)

    winter_storage_area.delete()

    # Test that all the directory have been removed
    assert not directory.exists()


def test_berth_is_available_no_leases(superuser_api_client, berth):
    assert Berth.objects.get(id=berth.id).is_available


@pytest.mark.parametrize("status", ["expired", "refused"])
@pytest.mark.parametrize("renew_automatically", [True, False])
def test_berth_is_available_lease_status(
    superuser_api_client, berth, status, renew_automatically
):
    BerthLeaseFactory(
        berth=berth, renew_automatically=renew_automatically, status=LeaseStatus(status)
    )
    assert Berth.objects.get(id=berth.id).is_available


def test_berth_is_available_last_season_dont_renew_automatically(
    superuser_api_client, berth
):
    start_date = calculate_berth_lease_start_date()
    end_date = calculate_berth_lease_end_date()

    start_date = start_date.replace(year=start_date.year - 1)
    end_date = end_date.replace(year=end_date.year - 1)

    BerthLeaseFactory(
        berth=berth, start_date=start_date, end_date=end_date, renew_automatically=False
    )
    assert Berth.objects.get(id=berth.id).is_available


@pytest.mark.parametrize("status", ["drafted", "offered", "expired", "refused"])
def test_berth_is_available_last_season_renew_automatically_invalid_status(
    superuser_api_client, berth, status
):
    start_date = calculate_berth_lease_start_date()
    end_date = calculate_berth_lease_end_date()

    start_date = start_date.replace(year=start_date.year - 1)
    end_date = end_date.replace(year=end_date.year - 1)

    BerthLeaseFactory(
        berth=berth,
        start_date=start_date,
        end_date=end_date,
        renew_automatically=False,
        status=LeaseStatus(status),
    )
    assert Berth.objects.get(id=berth.id).is_available


@freeze_time("2020-01-01T08:00:00Z")
@pytest.mark.parametrize("status", ["drafted", "offered", "paid", "expired", "refused"])
@pytest.mark.parametrize("renew_automatically", [True, False])
def test_berth_is_available_ends_during_season(
    superuser_api_client, berth, status, renew_automatically
):
    end_date = calculate_berth_lease_end_date()
    end_date = end_date.replace(month=end_date.month - 1)

    BerthLeaseFactory(
        berth=berth,
        end_date=end_date,
        renew_automatically=renew_automatically,
        status=LeaseStatus(status),
    )
    assert Berth.objects.get(id=berth.id).is_available


@freeze_time("2020-01-01T08:00:00Z")
@pytest.mark.parametrize("status", ["drafted", "offered", "paid"])
@pytest.mark.parametrize("renew_automatically", [True, False])
def test_berth_is_not_available_valid_through_whole_season(
    superuser_api_client, berth, status, renew_automatically
):
    BerthLeaseFactory(
        berth=berth, status=status, renew_automatically=renew_automatically
    )
    assert not Berth.objects.get(id=berth.id).is_available


@freeze_time("2020-01-01T08:00:00Z")
def test_berth_is_not_available_auto_renew_last_season(superuser_api_client, berth):
    start_date = calculate_berth_lease_start_date()
    end_date = calculate_berth_lease_end_date()

    start_date = start_date.replace(year=start_date.year - 1)
    end_date = end_date.replace(year=end_date.year - 1)
    BerthLeaseFactory(
        berth=berth,
        start_date=start_date,
        end_date=end_date,
        status=LeaseStatus.PAID,
        renew_automatically=True,
    )
    assert not Berth.objects.get(id=berth.id).is_available


def test_berth_type_is_assigned_new_price_group():
    assert BerthPriceGroup.objects.count() == 0
    width = round(random.uniform(1, 999), 2)

    berth_type = BerthTypeFactory(width=width)

    assert BerthType.objects.get(id=berth_type.id).price_group.name == f"{width}m"
    assert BerthPriceGroup.objects.count() == 1


def test_berth_type_is_assigned_existing_price_group():
    width = round(random.uniform(1, 999), 2)
    price_group = BerthPriceGroupFactory(name=f"{width}m")

    berth_type = BerthTypeFactory(width=width)

    assert BerthType.objects.get(id=berth_type.id).price_group == price_group


def test_pier_number_of_places():
    pier = PierFactory()
    free_berths = random.randint(1, 10)
    inactive_berths = random.randint(1, 10)

    for _berth in range(0, free_berths):
        BerthFactory(pier=pier, is_active=True)

    for _berth in range(0, inactive_berths):
        BerthFactory(pier=pier, is_active=False)

    pier = Pier.objects.get(pk=pier.pk)
    assert pier.number_of_free_places == free_berths
    assert pier.number_of_inactive_places == inactive_berths
    assert pier.number_of_places == free_berths + inactive_berths
