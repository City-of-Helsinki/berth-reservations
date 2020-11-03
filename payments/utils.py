import base64
import calendar
import random
import struct
import time
from datetime import date, timedelta
from decimal import Decimal
from functools import wraps
from typing import Callable, Optional, Union
from uuid import UUID

from dateutil.relativedelta import relativedelta
from dateutil.rrule import MONTHLY, rrule
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from django_ilmoitin.utils import send_notification

from applications.enums import ApplicationStatus
from customers.enums import OrganizationType
from leases.enums import LeaseStatus
from leases.utils import (
    calculate_season_end_date,
    calculate_season_start_date,
    calculate_winter_season_end_date,
    calculate_winter_season_start_date,
)
from payments.enums import OrderStatus, ProductServiceType
from resources.enums import AreaRegion
from resources.models import Harbor, WinterStorageArea
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
        season_days = (
            calculate_winter_season_end_date() - calculate_winter_season_start_date()
        )
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


@rounded
def calculate_organization_price(price, organization_type: OrganizationType) -> Decimal:
    if organization_type == OrganizationType.COMPANY:
        return price * 2
    elif organization_type == OrganizationType.NON_BILLABLE:
        return Decimal("0.00")
    else:
        return price


def calculate_organization_tax_percentage(tax, organization_type) -> Decimal:
    return (
        Decimal("0.00") if organization_type == OrganizationType.NON_BILLABLE else tax
    )


def price_as_fractional_int(price: Decimal) -> int:
    """
    Bambora requires amounts in fractional monetary units (e.g. 1€ = 100)
    """
    return int(rounded_decimal(price) * 100)


def generate_order_number() -> str:
    t = time.time() * 1000000 * random.uniform(1, 1000)
    b = base64.b32encode(struct.pack(">Q", int(t)).lstrip(b"\x00")).strip(b"=").lower()
    return b.decode("utf8")


def get_talpa_product_id(
    product_id: Union[UUID, str],
    area: Optional[Union[Harbor, WinterStorageArea]] = None,
):
    """
    The required ID for Talpa should have the following format:
    Tilino_Tulosyksikkö_Sisäinentilaus_Projekti_Toimintoalue_ALV-koodi_Vapaaehtoinenomatuotenumero

    Tilinumero                      Account number
    Tulosyksikkö                    Business unit
    Sisäinen Tilaus                 Internal Order
    Projekti                        Project
    Toimintoalue                    Function area
    ALV-koodi                       VAT code
    Vapaaehtoinen Oma Tuotenumero   Optional own product number
    """
    account_number = "340100"
    project = " "  # Empty
    vat_code = "44"  # Fixed
    own_product_number = str(product_id)
    business_unit = " "
    function_area = " "
    internal_order = " "

    if isinstance(area, Harbor):
        function_area = "292015"
    if isinstance(area, WinterStorageArea):
        function_area = "292014"

    if area:
        if area.region == AreaRegion.EAST:
            business_unit = "2923301"
            internal_order = "2923301100"
        elif area.region == AreaRegion.WEST:
            business_unit = "2923302"
            internal_order = "2923302200"

    return "_".join(
        [
            account_number,
            business_unit,
            internal_order,
            project,
            function_area,
            vat_code,
            own_product_number,
        ]
    )


def get_order_notification_type(order):
    from .enums import LeaseOrderType
    from .notifications import NotificationType

    if order.lease_order_type == LeaseOrderType.NEW_BERTH_ORDER:
        return NotificationType.NEW_BERTH_ORDER_APPROVED
    elif order.lease_order_type == LeaseOrderType.BERTH_SWITCH_ORDER:
        return NotificationType.BERTH_SWITCH_ORDER_APPROVED
    elif order.lease_order_type == LeaseOrderType.WINTER_STORAGE_ORDER:
        return NotificationType.NEW_WINTER_STORAGE_ORDER_APPROVED
    elif order.lease_order_type == LeaseOrderType.UNMARKED_WINTER_STORAGE_ORDER:
        return NotificationType.UNMARKED_WINTER_STORAGE_ORDER_APPROVED
    elif order.order_type == OrderType.RENEW_BERTH_ORDER:
        return NotificationType.RENEW_BERTH_ORDER_APPROVED
    else:
        raise ValidationError(_("Order does not have a valid type"))


def get_lease_status(new_status) -> LeaseStatus:
    if new_status == OrderStatus.PAID:
        return LeaseStatus.PAID
    elif new_status in (OrderStatus.REJECTED, OrderStatus.CANCELLED):
        return LeaseStatus.REFUSED
    elif new_status == OrderStatus.EXPIRED:
        return LeaseStatus.EXPIRED
    elif new_status == OrderStatus.WAITING:
        return LeaseStatus.OFFERED
    elif new_status == OrderStatus.ERROR:
        return LeaseStatus.ERROR
    else:
        raise ValidationError(_("Invalid order status"))


def approve_order(order, email, due_date: date, request: HttpRequest) -> None:
    from payments.providers import get_payment_provider

    # Update due date
    order.due_date = due_date
    order.save()

    language = settings.LANGUAGE_CODE

    if order.lease:
        # Update lease status
        order.lease.status = LeaseStatus.OFFERED
        order.lease.save()

        if order.lease.application:
            # Update application status
            order.lease.application.status = ApplicationStatus.OFFER_SENT
            order.lease.application.save()

            language = order.lease.application.language

    # Get payment URL
    payment_url = get_payment_provider(
        request, ui_return_url=settings.VENE_UI_RETURN_URL
    ).get_payment_email_url(order, lang=language)

    # Send email
    context = {
        "order": order,
        "fixed_services": order.order_lines.filter(
            product__service__in=ProductServiceType.FIXED_SERVICES()
        ),
        "optional_services": order.order_lines.filter(
            product__service__in=ProductServiceType.OPTIONAL_SERVICES()
        ),
        "payment_url": payment_url,
    }

    notification_type = get_order_notification_type(order)
    send_notification(email, notification_type.value, context, language)
