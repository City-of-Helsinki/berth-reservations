from datetime import date, datetime
from typing import List, Optional
from unittest.mock import patch

import pytest
import pytz
from django.conf import settings
from django.core.management import call_command
from factory.django import DjangoModelFactory
from freezegun import freeze_time

from applications.tests.factories import (
    BerthApplicationFactory,
    WinterStorageApplicationFactory,
)
from customers.tests.factories import BoatFactory
from leases.tests.factories import BerthLeaseFactory, WinterStorageLeaseFactory
from payments.tests.factories import OrderFactory


def _local_date_noon(value: date) -> datetime:
    return datetime(
        year=value.year,
        month=value.month,
        day=value.day,
        hour=12,
        minute=0,
        second=0,
        microsecond=0,
        tzinfo=pytz.timezone(settings.TIME_ZONE),
    )


def _create_test_order(
    order_email: Optional[str],
    lease_factory: DjangoModelFactory,
    application_factory: Optional[DjangoModelFactory] = None,
    application_email: Optional[str] = None,
):
    boat = BoatFactory()
    application = None
    if application_factory:
        application = application_factory(
            customer=boat.owner, boat=boat, email=application_email
        )
    lease = lease_factory(customer=boat.owner, boat=boat, application=application)
    return OrderFactory(lease=lease, customer_email=order_email)


def _create_get_customer_emails_minimal_test_data():
    _create_test_order(lease_factory=BerthLeaseFactory, order_email="test@example.org")


def _create_get_customer_emails_full_test_data():
    _create_test_order(lease_factory=BerthLeaseFactory, order_email=None)
    _create_test_order(lease_factory=WinterStorageLeaseFactory, order_email=None)
    for _ in range(2):  # Create a duplicate on purpose
        _create_test_order(
            lease_factory=BerthLeaseFactory, order_email="berth_1_primary@example.org"
        )
    _create_test_order(
        lease_factory=WinterStorageLeaseFactory,
        order_email="winter_storage_1_primary@example.org",
    )
    _create_test_order(
        application_factory=BerthApplicationFactory,
        lease_factory=BerthLeaseFactory,
        order_email=None,
        application_email="berth_fallback@example.org",
    )
    _create_test_order(
        application_factory=WinterStorageApplicationFactory,
        lease_factory=WinterStorageLeaseFactory,
        order_email=None,
        application_email="winter_storage_fallback@example.org",
    )
    _create_test_order(
        application_factory=BerthApplicationFactory,
        lease_factory=BerthLeaseFactory,
        order_email="berth_2_primary@example.org",
        application_email="berth_unused_fallback@example.org",
    )
    _create_test_order(
        application_factory=WinterStorageApplicationFactory,
        lease_factory=WinterStorageLeaseFactory,
        order_email="winter_storage_2_primary@example.org",
        application_email="winter_storage_unused_fallback@example.org",
    )


@freeze_time(_local_date_noon(date(2021, 1, 9)))
@pytest.mark.django_db
@pytest.mark.parametrize(
    "command_args,expected_output",
    [
        (
            [],
            (
                "berth_1_primary@example.org\n"
                "berth_2_primary@example.org\n"
                "berth_fallback@example.org\n"
                "winter_storage_1_primary@example.org\n"
                "winter_storage_2_primary@example.org\n"
                "winter_storage_fallback@example.org\n"
            ),
        ),
        (
            ["--exclude-winter-storage-orders"],
            (
                "berth_1_primary@example.org\n"
                "berth_2_primary@example.org\n"
                "berth_fallback@example.org\n"
            ),
        ),
        (
            ["--exclude-berth-orders"],
            (
                "winter_storage_1_primary@example.org\n"
                "winter_storage_2_primary@example.org\n"
                "winter_storage_fallback@example.org\n"
            ),
        ),
        (["--exclude-berth-orders", "--exclude-winter-storage-orders"], None),
    ],
)
def test_get_customer_emails_output(open_mock, capsys, command_args, expected_output):
    _create_get_customer_emails_full_test_data()
    with patch("payments.management.commands.get_customer_emails.open", open_mock):
        call_command("get_customer_emails", *command_args)

    captured = capsys.readouterr()
    if expected_output is None:
        open_mock.assert_not_called()
        assert "No emails found for date 2021-01-09" in captured.out
    else:
        open_mock.assert_called_once_with(
            "customer_emails_2021-01-09.txt", mode="w", encoding="utf-8", newline="\r\n"
        )
        open_mock.return_value.write.assert_called_once_with(expected_output)


@freeze_time(_local_date_noon(date(2021, 1, 9)))
@pytest.mark.django_db
@pytest.mark.parametrize("encoding", ["utf-8", "cp437", "cp1252"])
def test_get_customer_emails_encoding(open_mock, encoding):
    _create_get_customer_emails_minimal_test_data()
    with patch("payments.management.commands.get_customer_emails.open", open_mock):
        call_command("get_customer_emails", encoding=encoding)

    open_mock.assert_called_with(
        "customer_emails_2021-01-09.txt", mode="w", encoding=encoding, newline="\r\n"
    )


@freeze_time(_local_date_noon(date(2021, 1, 9)))
@pytest.mark.django_db
@pytest.mark.parametrize(
    "use_posix_line_separator,expected_newline", [(False, "\r\n"), (True, "\n")]
)
def test_get_customer_emails_use_posix_line_separator(
    open_mock, use_posix_line_separator: bool, expected_newline: str
):
    _create_get_customer_emails_minimal_test_data()
    with patch("payments.management.commands.get_customer_emails.open", open_mock):
        call_command(
            "get_customer_emails", use_posix_line_separator=use_posix_line_separator
        )

    open_mock.assert_called_with(
        "customer_emails_2021-01-09.txt",
        mode="w",
        encoding="utf-8",
        newline=expected_newline,
    )


@freeze_time(_local_date_noon(date(2022, 6, 30)))
@pytest.mark.django_db
@pytest.mark.parametrize(
    "expected_today_date,command_args",
    [
        (date(2022, 6, 30), []),
        (date(2020, 6, 30), ["--year=2020"]),
        (date(2020, 6, 30), ["-y2020"]),
        (date(2022, 8, 30), ["--month=8"]),
        (date(2022, 8, 30), ["-m8"]),
        (date(2022, 6, 25), ["--day=25"]),
        (date(2022, 6, 25), ["-d25"]),
        (date(2019, 12, 31), ["--year=2019", "--month=12", "--day=31"]),
        (date(2019, 12, 31), ["-y2019", "-m12", "-d31"]),
    ],
)
def test_get_customer_emails_year_month_day(
    open_mock, expected_today_date: date, command_args: List[str]
):
    with freeze_time(_local_date_noon(expected_today_date)):
        _create_get_customer_emails_minimal_test_data()

    with patch("payments.management.commands.get_customer_emails.open", open_mock):
        call_command("get_customer_emails", *command_args)

    open_mock.assert_called_once_with(
        f"customer_emails_{expected_today_date}.txt",
        mode="w",
        encoding="utf-8",
        newline="\r\n",
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "order_creation_date,today,expect_output",
    [
        # At the inclusive end of berth orders' date range
        (date(2021, 11, 30), date(2022, 9, 14), False),
        (date(2021, 12, 1), date(2022, 9, 14), True),
        (date(2022, 9, 14), date(2022, 9, 14), True),
        (date(2022, 9, 15), date(2022, 9, 14), False),
        # Just before the inclusive start of berth orders' date range
        (date(2021, 11, 30), date(2022, 11, 30), False),
        (date(2021, 12, 1), date(2022, 11, 30), True),
        (date(2022, 9, 14), date(2022, 11, 30), True),
        (date(2022, 9, 15), date(2022, 11, 30), False),
        # At the inclusive start of berth orders' date range
        (date(2022, 11, 30), date(2022, 12, 1), False),
        (date(2022, 12, 1), date(2022, 12, 1), True),
        (date(2023, 9, 14), date(2022, 12, 1), True),
        (date(2023, 9, 15), date(2022, 12, 1), False),
    ],
)
def test_get_customer_emails_berth_order_date_range(
    open_mock,
    capsys,
    order_creation_date: Optional[date],
    today: date,
    expect_output: bool,
):
    with freeze_time(_local_date_noon(order_creation_date)):
        _create_test_order(
            lease_factory=BerthLeaseFactory, order_email="test@example.org"
        )

    with patch("payments.management.commands.get_customer_emails.open", open_mock):
        with freeze_time(_local_date_noon(today)):
            call_command("get_customer_emails")

    if expect_output:
        open_mock.assert_called_once()
    else:
        open_mock.assert_not_called()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "order_creation_date,today,expect_output",
    [
        # At the inclusive end of winter storage orders' date range
        (date(2021, 7, 31), date(2022, 6, 9), False),
        (date(2021, 8, 1), date(2022, 6, 9), True),
        (date(2022, 6, 9), date(2022, 6, 9), True),
        (date(2022, 6, 10), date(2022, 6, 9), False),
        # Just before the inclusive start of winter storage orders' date range
        (date(2021, 7, 31), date(2022, 7, 31), False),
        (date(2021, 8, 1), date(2022, 7, 31), True),
        (date(2022, 6, 9), date(2022, 7, 31), True),
        (date(2022, 6, 10), date(2022, 7, 31), False),
        # At the inclusive start of winter storage orders' date range
        (date(2022, 7, 31), date(2022, 8, 1), False),
        (date(2022, 8, 1), date(2022, 8, 1), True),
        (date(2023, 6, 9), date(2022, 8, 1), True),
        (date(2023, 6, 10), date(2022, 8, 1), False),
    ],
)
def test_get_customer_emails_winter_storage_order_date_range(
    open_mock,
    capsys,
    order_creation_date: Optional[date],
    today: date,
    expect_output: bool,
):
    with freeze_time(_local_date_noon(order_creation_date)):
        _create_test_order(
            lease_factory=WinterStorageLeaseFactory, order_email="test@example.org"
        )

    with patch("payments.management.commands.get_customer_emails.open", open_mock):
        with freeze_time(_local_date_noon(today)):
            call_command("get_customer_emails")

    if expect_output:
        open_mock.assert_called_once()
    else:
        open_mock.assert_not_called()
