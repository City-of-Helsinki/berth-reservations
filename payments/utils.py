import calendar
from datetime import date, timedelta
from decimal import Decimal
from functools import wraps
from typing import Callable

from dateutil.relativedelta import relativedelta
from dateutil.rrule import MONTHLY, rrule

from leases.utils import calculate_season_end_date, calculate_season_start_date
from utils.numbers import rounded as rounded_decimal


def rounded(func):
    """
    Decorator for rounding function result
    """

    @wraps(func)
    def wrapped(*args, **kwargs):
        value = func(*args, **kwargs)
        return rounded_decimal(value)

    return wrapped


def currency_format(value):
    return f"{rounded_decimal(value)}€" if value else "-"


def currency(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        value = func(*args, **kwargs)
        return currency_format(value)

    return wrapped


def percentage_format(value):
    return f"{rounded_decimal(value)}%" if value else "-"


def percentage(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        value = func(*args, **kwargs)
        return percentage_format(value)

    return wrapped


@rounded
def convert_aftertax_to_pretax(aftertax_price, tax_percentage) -> Decimal:
    return aftertax_price / (1 + tax_percentage / 100)


def calculate_order_due_date(delta=14):
    return date.today() + timedelta(days=delta)


def _calculate_price_for_partial_month(
    month_date: date, base_price: Decimal, days: Callable[[int], int]
) -> Decimal:
    _, days_in_month = calendar.monthrange(month_date.year, month_date.month)
    price_per_day = base_price / days_in_month
    return days(days_in_month) * price_per_day


@rounded
def calculate_product_partial_month_price(
    base_price: Decimal, start_date: date, end_date: date
) -> Decimal:
    price = Decimal(0)

    # If the dates are on the same month/year
    if start_date.month == end_date.month and start_date.year == end_date.year:
        price = _calculate_price_for_partial_month(
            start_date, base_price, days=lambda _: (end_date - start_date).days
        )
    else:
        # Calculate price for the start month
        price += _calculate_price_for_partial_month(
            start_date,
            base_price,
            days=lambda days_in_month: days_in_month - start_date.day + 1,
        )

        # Calculate price for the months in between
        months_between = list(
            rrule(
                MONTHLY,
                dtstart=start_date + relativedelta(day=1, months=1),
                until=end_date - relativedelta(day=1, months=1),
            )
        )
        # Calculate the added price for all the complete months in between
        price += len(months_between) * base_price

        # Calculate price for the end month
        price += _calculate_price_for_partial_month(
            end_date, base_price, days=lambda _: end_date.day - 1,
        )

    return price


@rounded
def calculate_product_partial_season_price(
    base_price: Decimal, start_date: date, end_date: date, summer_season: bool = True
) -> Decimal:
    # If it's the "normal" (summer) season, calculate with the normal dates
    season_days = calculate_season_end_date() - calculate_season_start_date()
    # If it's for the opposite season ("winter season"), calculate the inverse
    if not summer_season:
        # Calculate the amount of days in the year, in case it's a leap year
        days_in_year = (start_date + relativedelta(years=1)) - start_date
        season_days = days_in_year - season_days
    delta = (end_date - start_date).days
    price = (delta * base_price) / season_days.days
    return price


@rounded
def calculate_product_partial_year_price(
    base_price: Decimal, start_date: date, end_date: date
) -> Decimal:
    days_in_year = (
        366
        if calendar.isleap(start_date.year) or calendar.isleap(end_date.year)
        else 365
    )
    delta = (end_date - start_date).days
    price = (delta * base_price) / days_in_year
    return price


@rounded
def calculate_product_percentage_price(base_price, percentage):
    return base_price * (percentage / 100)
