import xlrd
from freezegun import freeze_time

from ..models import HarborChoice, Reservation
from ..utils import export_reservations_as_xlsx
from .factories import ReservationFactory


@freeze_time("2019-01-14T08:00:00Z")
def test_exporting_reservations_to_excel(boat_type, harbor):
    reservation_data = {
        "first_name": "Kyösti",
        "last_name": "Testaaja",
        "email": "kyosti.testaaja@example.com",
        "address": "Mariankatu 2",
        "zip_code": "00170",
        "municipality": "Helsinki",
        "phone_number": "0411234567",
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
    reservation = ReservationFactory(**reservation_data)
    HarborChoice.objects.create(reservation=reservation, priority=1, harbor=harbor)

    queryset = Reservation.objects.all()
    xlsx_bytes = export_reservations_as_xlsx(queryset)
    wb = xlrd.open_workbook(file_contents=xlsx_bytes)

    assert "berth_reservations" in wb.sheet_names()

    xl_sheet = wb.sheet_by_name("berth_reservations")
    row = xl_sheet.row(1)

    boat_type.set_current_language("fi")

    assert xl_sheet.ncols == 31

    assert row[0].value == "2019-01-14 10:00"
    assert row[1].value == "1: Aurinkoinen satama"
    assert row[2].value == "Kyösti"
    assert row[3].value == "Testaaja"
    assert row[4].value == "kyosti.testaaja@example.com"
    assert row[5].value == "Mariankatu 2"
    assert row[6].value == "00170"
    assert row[7].value == "Helsinki"
    assert row[8].value == "0411234567"
    assert row[9].value == boat_type.name
    assert row[10].value == 2.0
    assert row[11].value == 3.5
    assert row[12].value == 1
    assert row[13].value == 20000
    assert row[14].value == "B0A7"
    assert row[15].value == "Vene"
    assert row[16].value == "BMW S 12"
    assert row[17].value == "Yes"
    assert row[18].value == ""
    assert row[19].value == ""
    assert row[20].value == ""
    assert row[21].value == "Yes"
    assert row[22].value == "wood"
    assert row[23].value == "cafe"
    assert row[24].value == "a while"
    assert row[25].value == "01.02.2019"
    assert row[26].value == "01.03.2019"
    assert row[27].value == "Yes"
    assert row[28].value == "Yes"
    assert row[29].value == "Yes"
    assert row[30].value == "1234567890"
