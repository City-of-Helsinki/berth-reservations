import pytest
import xlrd
from freezegun import freeze_time

from ..enums import WinterStorageMethod
from ..models import (
    BerthApplication,
    HarborChoice,
    WinterStorageApplication,
    WinterStorageAreaChoice,
)
from ..utils import (
    export_berth_applications_as_xlsx,
    export_winter_storage_applications_as_xlsx,
)
from .factories import BerthApplicationFactory, WinterStorageApplicationFactory


@freeze_time("2019-01-14T08:00:00Z")
@pytest.mark.parametrize("berth_switch", [True, False])
def test_exporting_berth_applications_to_excel(
    berth_switch, boat_type, harbor, berth_switch_info
):
    application_data = {
        "first_name": "Kyösti",
        "last_name": "Testaaja",
        "email": "kyosti.testaaja@example.com",
        "address": "Mariankatu 2",
        "zip_code": "00170",
        "municipality": "Helsinki",
        "phone_number": "0411234567",
        "berth_switch": berth_switch_info if berth_switch else None,
        "boat_type": boat_type,
        "boat_width": "2",
        "boat_length": "3.5",
        "boat_draught": "1",
        "boat_weight": 20000,
        "boat_registration_number": "B0A7",
        "boat_name": "Vene",
        "boat_model": "BMW S 12",
        "accessibility_required": True,
        "accept_boating_newsletter": False,
        "accept_fitness_news": False,
        "accept_library_news": False,
        "accept_other_culture_news": True,
        "boat_hull_material": "wood",
        "boat_intended_use": "cafe",
        "renting_period": "a while",
        "rent_from": "01.02.2019",
        "rent_till": "01.03.2019",
        "boat_is_insured": True,
        "boat_is_inspected": True,
        "agree_to_terms": True,
        "application_code": "1234567890",
    }
    application = BerthApplicationFactory(**application_data)
    HarborChoice.objects.create(application=application, priority=1, harbor=harbor)

    queryset = BerthApplication.objects.all()
    xlsx_bytes = export_berth_applications_as_xlsx(queryset)
    wb = xlrd.open_workbook(file_contents=xlsx_bytes)

    assert "berth_applications" in wb.sheet_names()

    xl_sheet = wb.sheet_by_name("berth_applications")
    row = xl_sheet.row(1)

    boat_type.set_current_language("fi")

    expected_berth_switch_str = ""
    if berth_switch:
        expected_berth_switch_str = "{} ({}): {}".format(
            berth_switch_info.harbor.name,
            berth_switch_info.pier,
            berth_switch_info.berth_number,
        )

    assert xl_sheet.ncols == 32

    assert row[0].value == "2019-01-14 10:00"
    assert row[1].value == "1: Aurinkoinen satama"
    assert row[2].value == expected_berth_switch_str
    assert row[3].value == "Kyösti"
    assert row[4].value == "Testaaja"
    assert row[5].value == "kyosti.testaaja@example.com"
    assert row[6].value == "Mariankatu 2"
    assert row[7].value == "00170"
    assert row[8].value == "Helsinki"
    assert row[9].value == "0411234567"
    assert row[10].value == boat_type.name
    assert row[11].value == 2.0
    assert row[12].value == 3.5
    assert row[13].value == 1
    assert row[14].value == 20000
    assert row[15].value == "B0A7"
    assert row[16].value == "Vene"
    assert row[17].value == "BMW S 12"
    assert row[18].value == "Yes"
    assert row[19].value == ""
    assert row[20].value == ""
    assert row[21].value == ""
    assert row[22].value == "Yes"
    assert row[23].value == "wood"
    assert row[24].value == "cafe"
    assert row[25].value == "a while"
    assert row[26].value == "01.02.2019"
    assert row[27].value == "01.03.2019"
    assert row[28].value == "Yes"
    assert row[29].value == "Yes"
    assert row[30].value == "Yes"
    assert row[31].value == "1234567890"


@freeze_time("2019-01-14T08:00:00Z")
def test_exporting_winter_storage_applications_to_excel(boat_type, winter_area):
    application_data = {
        "first_name": "Kyösti",
        "last_name": "Testaaja",
        "email": "kyosti.testaaja@example.com",
        "address": "Mariankatu 2",
        "zip_code": "00170",
        "municipality": "Helsinki",
        "phone_number": "0411234567",
        "storage_method": WinterStorageMethod.ON_TRESTLES,
        "trailer_registration_number": "hel001",
        "boat_type": boat_type,
        "boat_width": "2",
        "boat_length": "3.5",
        "boat_registration_number": "B0A7",
        "boat_name": "Vene",
        "boat_model": "BMW S 12",
        "accept_boating_newsletter": False,
        "accept_fitness_news": False,
        "accept_library_news": False,
        "accept_other_culture_news": True,
        "application_code": "1234567890",
    }
    application = WinterStorageApplicationFactory(**application_data)
    WinterStorageAreaChoice.objects.create(
        application=application, priority=1, winter_storage_area=winter_area
    )

    queryset = WinterStorageApplication.objects.all()
    xlsx_bytes = export_winter_storage_applications_as_xlsx(queryset)
    wb = xlrd.open_workbook(file_contents=xlsx_bytes)

    assert "winter_storage_applications" in wb.sheet_names()

    xl_sheet = wb.sheet_by_name("winter_storage_applications")
    row = xl_sheet.row(1)

    boat_type.set_current_language("fi")

    assert xl_sheet.ncols == 22

    assert row[0].value == "2019-01-14 10:00"
    assert row[1].value == "1: {}".format(winter_area.name)
    assert row[2].value == "Kyösti"
    assert row[3].value == "Testaaja"
    assert row[4].value == "kyosti.testaaja@example.com"
    assert row[5].value == "Mariankatu 2"
    assert row[6].value == "00170"
    assert row[7].value == "Helsinki"
    assert row[8].value == "0411234567"
    assert row[9].value == WinterStorageMethod.ON_TRESTLES.label
    assert row[10].value == "hel001"
    assert row[11].value == boat_type.name
    assert row[12].value == 2.0
    assert row[13].value == 3.5
    assert row[14].value == "B0A7"
    assert row[15].value == "Vene"
    assert row[16].value == "BMW S 12"
    assert row[17].value == ""
    assert row[18].value == ""
    assert row[19].value == ""
    assert row[20].value == "Yes"
    assert row[21].value == "1234567890"
