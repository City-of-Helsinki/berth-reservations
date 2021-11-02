from datetime import date

import pytest  # noqa
from dateutil.utils import today
from freezegun import freeze_time

from ..utils import calculate_lease_start_and_end_dates


@freeze_time("2020-01-01T08:00:00Z")
def test_calculate_lease_start_and_end_dates_before_season():
    """Dates between 1.1 and 9.6"""

    expected_start = date(year=2020, month=6, day=10)
    expected_end = date(year=2020, month=9, day=14)

    start, end = calculate_lease_start_and_end_dates(today().date())

    assert start == expected_start
    assert end == expected_end


@freeze_time("2020-08-01T08:00:00Z")
def test_calculate_lease_start_and_end_dates_during_season():
    """Dates between 10.6 and 14.9"""

    expected_start = date(year=2020, month=8, day=1)
    expected_end = date(year=2020, month=9, day=14)

    start, end = calculate_lease_start_and_end_dates(today().date())

    assert start == expected_start
    assert end == expected_end


@freeze_time("2020-10-01T08:00:00Z")
def test_calculate_lease_start_and_end_dates_after_season():
    """Dates between 15.9 and 31.12"""

    expected_start = date(year=2021, month=6, day=10)
    expected_end = date(year=2021, month=9, day=14)

    start, end = calculate_lease_start_and_end_dates(today().date())

    assert start == expected_start
    assert end == expected_end
