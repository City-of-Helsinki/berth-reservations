from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Order
    from .notifications import NotificationType

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

from babel.dates import format_date
from dateutil.relativedelta import relativedelta
from dateutil.rrule import MONTHLY, rrule
from dateutil.utils import today
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from django_ilmoitin.utils import send_notification

from applications.enums import ApplicationStatus
from berth_reservations.exceptions import VenepaikkaGraphQLError
from customers.enums import OrganizationType
from customers.services import (
    HelsinkiProfileUser,
    ProfileService,
    SMSNotificationService,
)
from leases.enums import LeaseStatus
from leases.utils import (
    calculate_season_end_date,
    calculate_season_start_date,
    calculate_winter_season_end_date,
    calculate_winter_season_start_date,
)
from resources.enums import AreaRegion
from resources.models import Harbor, WinterStorageArea
from utils.email import is_valid_email
from utils.numbers import rounded as rounded_decimal

from .enums import OrderStatus, OrderType, ProductServiceType


def fetch_order_profile(order, profile_token):
    profile = ProfileService(profile_token=profile_token).get_profile(order.customer.id)
    return profile


def update_order_from_profile(order, profile):
    order.customer_first_name = profile.first_name
    order.customer_last_name = profile.first_name
    order.customer_email = profile.email
    order.customer_phone = profile.phone
    order.customer_address = profile.address
    order.customer_zip_code = profile.postal_code
    order.customer_city = profile.city
    order.save()
    return profile


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

    if order.order_type == OrderType.ADDITIONAL_PRODUCT_ORDER:
        return NotificationType.ADDITIONAL_PRODUCT_ORDER_APPROVED
    elif order.lease_order_type == LeaseOrderType.NEW_BERTH_ORDER:
        return NotificationType.NEW_BERTH_ORDER_APPROVED
    elif order.lease_order_type == LeaseOrderType.BERTH_SWITCH_ORDER:
        return NotificationType.BERTH_SWITCH_ORDER_APPROVED
    elif order.lease_order_type == LeaseOrderType.WINTER_STORAGE_ORDER:
        return NotificationType.NEW_WINTER_STORAGE_ORDER_APPROVED
    elif order.lease_order_type == LeaseOrderType.UNMARKED_WINTER_STORAGE_ORDER:
        return NotificationType.UNMARKED_WINTER_STORAGE_ORDER_APPROVED
    elif order.lease_order_type == LeaseOrderType.RENEW_BERTH_ORDER:
        return NotificationType.RENEW_BERTH_ORDER_APPROVED
    else:
        raise ValidationError(_("Order does not have a valid type"))


def get_lease_status(new_status) -> LeaseStatus:
    # return None if lease status need not be changed
    if new_status in OrderStatus.get_paid_statuses():
        return LeaseStatus.PAID
    elif new_status == OrderStatus.REJECTED:
        return LeaseStatus.REFUSED
    elif new_status == OrderStatus.EXPIRED:
        return LeaseStatus.EXPIRED
    elif new_status == OrderStatus.WAITING:
        return LeaseStatus.OFFERED
    elif new_status == OrderStatus.ERROR:
        return LeaseStatus.ERROR
    elif new_status in (OrderStatus.CANCELLED, OrderStatus.REFUNDED):
        return None
    else:
        raise ValidationError(_("Invalid order status"))


def get_application_status(new_status) -> ApplicationStatus:
    # return None if application status need not be changed
    if new_status == OrderStatus.REJECTED:
        return ApplicationStatus.REJECTED
    elif new_status in OrderStatus.get_paid_statuses():
        return ApplicationStatus.HANDLED
    else:
        return None


def approve_order(
    order,
    email,
    due_date: date,
    helsinki_profile_user: HelsinkiProfileUser,
    request: HttpRequest,
) -> None:
    if helsinki_profile_user:
        order.customer_first_name = helsinki_profile_user.first_name
        order.customer_last_name = helsinki_profile_user.last_name
        order.customer_email = helsinki_profile_user.email
        order.customer_phone = helsinki_profile_user.phone
        order.customer_address = helsinki_profile_user.address
        order.customer_zip_code = helsinki_profile_user.postal_code
        order.customer_city = helsinki_profile_user.city

    order.due_date = due_date
    order.save()

    if order.lease and order.order_type == OrderType.LEASE_ORDER:
        # Update lease status
        order.lease.status = LeaseStatus.OFFERED
        order.lease.save()

        if order.lease.application:
            # Update application status
            order.lease.application.status = ApplicationStatus.OFFER_SENT
            order.lease.application.save()

    if order.customer.is_non_billable_customer():
        order.set_status(OrderStatus.PAID_MANUALLY, "Non-billable customer.")
    else:
        send_payment_notification(
            order, request, email, phone_number=order.customer_phone
        )


def send_cancellation_notice(order):
    from .notifications import NotificationType

    language = (
        order.lease.application.language
        if order.lease and order.lease.application
        else settings.LANGUAGE_CODE
    )
    notification_type = NotificationType.ORDER_CANCELLED
    if rejected_at := getattr(order, "rejected_at", None):
        rejected_at = format_date(rejected_at, locale=language)
    context = {
        "order": order,
        "rejected_at": rejected_at,
        "subject": get_email_subject(notification_type),
    }
    email = order.customer_email
    if not email:
        if order.lease and order.lease.application:
            email = order.lease.application.email
        else:
            raise VenepaikkaGraphQLError(_("No email was found"))

    send_notification(email, notification_type.value, context, language)


def send_refund_notice(order):
    from .notifications import NotificationType

    language = (
        order.lease.application.language
        if order.lease and order.lease.application
        else settings.LANGUAGE_CODE
    )
    notification_type = NotificationType.ORDER_REFUNDED

    context = get_context(
        order, notification_type, has_services=False, payment_url=None, cancel_url=None
    )

    email = order.customer_email

    if not email:
        if order.lease and order.lease.application:
            email = order.lease.application.email
        else:
            raise VenepaikkaGraphQLError(_("No email was found"))

    send_notification(email, notification_type.value, context, language)


def prepare_for_resending(order):
    if order.status == OrderStatus.ERROR or order.lease.status == LeaseStatus.ERROR:
        order.set_status(
            OrderStatus.WAITING,
            comment=f"{today()}: {_('Cleanup the invoice to attempt resending')}\n",
        )
    elif order.status == OrderStatus.CANCELLED:
        order.set_status(
            OrderStatus.WAITING,
            comment=f"{today()}: {_('Resend cancelled invoice')}\n",
        )


def resend_order(order, due_date: date, request: HttpRequest) -> None:
    if order.lease.status != LeaseStatus.OFFERED:
        raise ValueError(_("Cannot resend an order for a lease not in status OFFERED"))

    if due_date:
        order.due_date = due_date

    order.recalculate_price()
    order.save()

    send_payment_notification(order, request)


def send_payment_notification(
    order: Order,
    request: HttpRequest,
    email: str = None,
    phone_number: str = None,
    has_services: bool = True,
    has_payment_urls: bool = True,
):
    from payments.providers import get_payment_provider

    from .notifications import NotificationType

    order_email = email or order.customer_email
    order_phone = phone_number or order.customer_phone

    if not is_valid_email(order_email):
        raise ValidationError(_("Missing customer email"))

    language = get_notification_language(order)

    payment_url = None
    cancel_url = None

    if has_payment_urls:
        payment_url = get_payment_provider(
            request, ui_return_url=settings.VENE_UI_RETURN_URL
        ).get_payment_email_url(order, lang=language)

        cancel_url = get_payment_provider(
            request, ui_return_url=settings.VENE_UI_RETURN_URL
        ).get_cancellation_email_url(order, lang=language)

    notification_type = get_order_notification_type(order)
    context = get_context(
        order, notification_type, has_services, payment_url, cancel_url
    )
    send_notification(order_email, notification_type.value, context, language)

    if order_phone and notification_type not in (
        NotificationType.ORDER_CANCELLED,
        NotificationType.ORDER_REFUNDED,
    ):
        if hasattr(order, "product") and order.product:
            product_name = order.product.name
        else:
            product_name = ", ".join(
                [
                    str(ProductServiceType(order_line.product.service).label)
                    for order_line in order.order_lines.all()
                ]
            )

        sms_context = {
            "product_name": product_name,
            "due_date": format_date(order.due_date, locale=language),
            "payment_url": payment_url,
        }
        sms_service = SMSNotificationService()
        sms_service.send(
            NotificationType.SMS_INVOICE_NOTICE,
            sms_context,
            order_phone,
            language=language,
        )


def get_notification_language(order):
    language = settings.LANGUAGE_CODE
    if order.lease and order.lease.application:
        language = order.lease.application.language
    return language


def get_email_subject(notification_type):
    from .notifications import NotificationType

    if (
        notification_type == NotificationType.NEW_BERTH_ORDER_APPROVED
        or notification_type == NotificationType.RENEW_BERTH_ORDER_APPROVED
    ):
        return _("Boat berth invoice")
    if notification_type == NotificationType.ORDER_CANCELLED:
        return _("Confirmation")
    if notification_type == NotificationType.ORDER_REFUNDED:
        return _("Refund confirmation")
    return notification_type.label


def get_context(
    order: Order,
    notification_type: NotificationType,
    has_services: bool = True,
    payment_url: str = None,
    cancel_url: str = None,
):
    if order.order_type == OrderType.LEASE_ORDER:
        context = {
            "subject": get_email_subject(notification_type),
            "order": order,
        }

        if has_services:
            context["fixed_services"] = order.order_lines.filter(
                product__service__in=ProductServiceType.FIXED_SERVICES()
            )
            context["optional_services"] = (
                order.order_lines.filter(
                    product__service__in=ProductServiceType.OPTIONAL_SERVICES()
                ),
            )

        if payment_url:
            context["payment_url"] = payment_url
        if cancel_url:
            context["cancel_url"] = cancel_url

        return context
    else:
        # We currently support only STORAGE_ON_ICE additional product orders,
        # so this is very specific implementation for now
        start_date = calculate_winter_season_start_date(order.lease.end_date)
        start_year = start_date.year
        end_year = start_year + 1
        season = "{} - {}".format(start_year, end_year)
        additional_product_name = (
            order.order_lines.first().product.get_service_display()
        )

        return {
            "subject": get_email_subject(notification_type),
            "order": order,
            "additional_product": {"name": additional_product_name, "season": season},
            "payment_url": payment_url,
        }
