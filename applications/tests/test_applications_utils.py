import pytest
import xlrd
from django.conf import settings
from freezegun import freeze_time

from customers.tests.factories import BoatFactory
from resources.tests.factories import (
    BoatTypeFactory,
    HarborFactory,
    WinterStorageAreaFactory,
)

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

EXCEL_FILE_LANG = settings.LANGUAGES[0][0]


@freeze_time("2019-01-14T08:00:00Z")
@pytest.mark.parametrize("berth_switch", [True, False])
@pytest.mark.parametrize("customer_private", [True, False])
# Parametrised berth_switch_reason inside berth_switch
@pytest.mark.parametrize("berth_switch_info", [True, False], indirect=True)
def test_exporting_berth_applications_to_excel(
    berth_switch,
    berth_switch_info,
    customer_private,
):
    harbor = HarborFactory(name="Satama")
    harbor.create_translation("fi", name="Satama")
    boat_type = BoatTypeFactory()
    boat_type.create_translation("fi", name="Jollapaikka")
    boat_data = {
        "boat_type": boat_type,
        "width": "2",
        "length": "3.5",
        "draught": "1",
        "weight": 20000,
        "registration_number": "B0A7",
        "name": "Vene",
        "model": "BMW S 12",
        "hull_material": "wood",
        "intended_use": "cafe",
        "is_insured": True,
        "is_inspected": True,
    }
    application_data = {
        "first_name": "Kyösti",
        "last_name": "Testaaja",
        "email": "kyosti.testaaja@example.com",
        "address": "Mariankatu 2",
        "zip_code": "00170",
        "municipality": "Helsinki",
        "phone_number": "0411234567",
        "berth_switch": berth_switch_info if berth_switch else None,
        "accessibility_required": True,
        "accept_boating_newsletter": False,
        "accept_fitness_news": False,
        "accept_library_news": False,
        "accept_other_culture_news": True,
        "renting_period": "a while",
        "rent_from": "01.02.2019",
        "rent_till": "01.03.2019",
        "agree_to_terms": True,
        "application_code": "1234567890",
    }
    if not customer_private:
        application_data["company_name"] = "ACME Inc."
        application_data["business_id"] = "123123-000"
    boat = BoatFactory(**boat_data)
    application = BerthApplicationFactory(**application_data, boat=boat)
    HarborChoice.objects.create(application=application, priority=1, harbor=harbor)

    queryset = BerthApplication.objects.all()
    xlsx_bytes = export_berth_applications_as_xlsx(queryset)
    wb = xlrd.open_workbook(file_contents=xlsx_bytes)

    assert "berth_applications" in wb.sheet_names()

    xl_sheet = wb.sheet_by_name("berth_applications")
    row = xl_sheet.row(1)

    expected_berth_switch_reason = ""
    expected_berth_switch_str = ""
    if berth_switch:
        switch_harbor_name = (
            berth_switch_info.berth.pier.harbor.safe_translation_getter(
                "name", language_code=EXCEL_FILE_LANG
            )
        )
        expected_berth_switch_str = "{} ({}): {}".format(
            switch_harbor_name,
            berth_switch_info.berth.pier.identifier,
            berth_switch_info.berth.number,
        )
        expected_berth_switch_reason = (
            berth_switch_info.reason.title if berth_switch_info.reason else "---"
        )

    harbor_name = harbor.safe_translation_getter("name", language_code=EXCEL_FILE_LANG)
    boat_type_name = boat_type.safe_translation_getter(
        "name", language_code=EXCEL_FILE_LANG
    )

    assert xl_sheet.ncols == 35

    assert row[0].value == "2019-01-14 10:00"
    assert row[1].value == "1: {}".format(harbor_name)
    assert row[2].value == expected_berth_switch_str
    assert row[3].value == expected_berth_switch_reason
    assert row[4].value == ("" if customer_private else "ACME Inc.")
    assert row[5].value == ("" if customer_private else "123123-000")
    assert row[6].value == "Kyösti"
    assert row[7].value == "Testaaja"
    assert row[8].value == "kyosti.testaaja@example.com"
    assert row[9].value == "Mariankatu 2"
    assert row[10].value == "00170"
    assert row[11].value == "Helsinki"
    assert row[12].value == "0411234567"
    assert row[13].value == boat_type_name
    assert row[14].value == 2.0
    assert row[15].value == 3.5
    assert row[16].value == 1
    assert row[17].value == 20000
    assert row[18].value == "B0A7"
    assert row[19].value == "Vene"
    assert row[20].value == "BMW S 12"
    assert row[21].value == "Yes"
    assert row[22].value == ""
    assert row[23].value == ""
    assert row[24].value == ""
    assert row[25].value == "Yes"
    assert row[26].value == "wood"
    assert row[27].value == "cafe"
    assert row[28].value == "a while"
    assert row[29].value == "01.02.2019"
    assert row[30].value == "01.03.2019"
    assert row[31].value == "Yes"
    assert row[32].value == "Yes"
    assert row[33].value == "Yes"
    assert row[34].value == "1234567890"


@freeze_time("2019-01-14T08:00:00Z")
@pytest.mark.parametrize("customer_private", [True, False])
def test_exporting_winter_storage_applications_to_excel(customer_private):
    winter_area = WinterStorageAreaFactory(name="Satama")
    winter_area.create_translation("fi", name="Satama")
    boat_type = BoatTypeFactory()
    boat_type.create_translation("fi", name="Jollapaikka")
    boat_data = {
        "boat_type": boat_type,
        "width": "2",
        "length": "3.5",
        "registration_number": "B0A7",
        "name": "Vene",
        "model": "BMW S 12",
    }
    application_data = {
        "first_name": "Kyösti",
        "last_name": "Testaaja",
        "email": "kyosti.testaaja@example.com",
        "address": "Mariankatu 2",
        "zip_code": "00170",
        "municipality": "Helsinki",
        "phone_number": "0411234567",
        "storage_method": WinterStorageMethod.ON_TRESTLES.value,
        "trailer_registration_number": "hel001",
        "accept_boating_newsletter": False,
        "accept_fitness_news": False,
        "accept_library_news": False,
        "accept_other_culture_news": True,
        "application_code": "1234567890",
    }
    if not customer_private:
        application_data["company_name"] = "ACME Inc."
        application_data["business_id"] = "123123-000"

    boat = BoatFactory(**boat_data)
    application = WinterStorageApplicationFactory(**application_data, boat=boat)
    WinterStorageAreaChoice.objects.create(
        application=application, priority=1, winter_storage_area=winter_area
    )

    queryset = WinterStorageApplication.objects.all()
    xlsx_bytes = export_winter_storage_applications_as_xlsx(queryset)
    wb = xlrd.open_workbook(file_contents=xlsx_bytes)

    assert "winter_storage_applications" in wb.sheet_names()

    xl_sheet = wb.sheet_by_name("winter_storage_applications")
    row = xl_sheet.row(1)

    winter_area_name = winter_area.safe_translation_getter(
        "name", language_code=EXCEL_FILE_LANG
    )
    boat_type_name = boat_type.safe_translation_getter(
        "name", language_code=EXCEL_FILE_LANG
    )

    assert xl_sheet.ncols == 24

    assert row[0].value == "2019-01-14 10:00"
    assert row[1].value == "1: {}".format(winter_area_name)
    assert row[2].value == ("" if customer_private else "ACME Inc.")
    assert row[3].value == ("" if customer_private else "123123-000")
    assert row[4].value == "Kyösti"
    assert row[5].value == "Testaaja"
    assert row[6].value == "kyosti.testaaja@example.com"
    assert row[7].value == "Mariankatu 2"
    assert row[8].value == "00170"
    assert row[9].value == "Helsinki"
    assert row[10].value == "0411234567"
    assert row[11].value == WinterStorageMethod.ON_TRESTLES.label
    assert row[12].value == "hel001"
    assert row[13].value == boat_type_name
    assert row[14].value == 2.0
    assert row[15].value == 3.5
    assert row[16].value == "B0A7"
    assert row[17].value == "Vene"
    assert row[18].value == "BMW S 12"
    assert row[19].value == ""
    assert row[20].value == ""
    assert row[21].value == ""
    assert row[22].value == "Yes"
    assert row[23].value == "1234567890"
