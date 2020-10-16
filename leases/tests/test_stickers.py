from datetime import date

from leases.stickers import get_next_sticker_number, get_ws_sticker_season


def test_get_ws_sticker_season():
    assert get_ws_sticker_season(date(year=2020, month=9, day=10)) == "2020_2021"
    assert get_ws_sticker_season(date(year=2021, month=1, day=10)) == "2020_2021"
    assert get_ws_sticker_season(date(year=2021, month=7, day=10)) == "2021_2022"


def test_get_next_sticker_number(sticker_sequences):
    lease_start = date(year=2020, month=9, day=10)
    assert get_next_sticker_number(lease_start) == 1
    assert get_next_sticker_number(lease_start) == 2
    assert get_next_sticker_number(lease_start) == 3

    lease_start = date(year=2023, month=9, day=10)
    assert get_next_sticker_number(lease_start) == 1
    assert get_next_sticker_number(lease_start) == 2
