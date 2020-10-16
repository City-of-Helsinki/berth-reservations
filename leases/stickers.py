from datetime import date

from django.db import connection

from leases.utils import calculate_winter_season_start_date


def get_next_sticker_number(lease_start: date) -> int:
    with connection.cursor() as cursor:
        sticker_season = get_ws_sticker_season(lease_start)
        sequence_name = "ws_stickers_" + sticker_season

        cursor.execute("SELECT nextval(%s)", [sequence_name])
        return cursor.fetchone()[0]


def get_ws_sticker_season(lease_start: date) -> str:
    start_date = calculate_winter_season_start_date(lease_start)
    start_year = start_date.year
    end_year = start_year + 1
    return "{}_{}".format(start_year, end_year)


def create_ws_sticker_sequences() -> None:
    """Creates WS sticker sequences for next 25 years"""
    with connection.cursor() as cursor:
        start_year = 2020
        for i in range(25):
            year = start_year + i
            sql = "CREATE SEQUENCE IF NOT EXISTS ws_stickers_{}_{} START 1;".format(
                year, year + 1
            )
            cursor.execute(sql)
