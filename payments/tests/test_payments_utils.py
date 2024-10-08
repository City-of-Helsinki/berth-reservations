from decimal import Decimal

import pytest
from dateutil.utils import today
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import RequestFactory
from django.utils import timezone

from applications.enums import ApplicationStatus
from leases.enums import LeaseStatus
from payments.enums import OrderStatus, PricingCategory
from payments.models import (
    DEFAULT_TAX_PERCENTAGE,
    Order,
    VAT_10,
    VAT_14,
    VAT_24,
    VAT_25_5,
)
from payments.utils import (
    _get_vasikkasaari_harbor,
    approve_order,
    get_berth_product_pricing_category,
    is_24_percent,
    send_payment_notification,
    tax_percentage_as_string,
)
from resources.enums import BerthMooringType


@pytest.mark.parametrize(
    "order",
    ["berth_order", "winter_storage_order"],
    indirect=True,
)
def test_approve_order(
    order: Order,
    bambora_payment_provider,
    notification_template_orders_approved,
    helsinki_profile_user,
):
    order.status = OrderStatus.DRAFTED
    order.save(update_fields=["status"])

    request = RequestFactory().request()
    due_date = today().date()
    approve_order(
        order, order.lease.application.email, due_date, helsinki_profile_user, request
    )

    order.refresh_from_db()

    assert order.due_date == due_date
    assert order.lease.status == LeaseStatus.OFFERED
    assert order.lease.application.status == ApplicationStatus.OFFER_SENT

    assert order.customer_first_name == helsinki_profile_user.first_name
    assert order.customer_last_name == helsinki_profile_user.last_name
    assert order.customer_email == helsinki_profile_user.email
    assert order.customer_address == helsinki_profile_user.address
    assert order.customer_zip_code == helsinki_profile_user.postal_code
    assert order.customer_city == helsinki_profile_user.city

    payment_url = bambora_payment_provider.get_payment_email_url(
        order, lang=order.lease.application.language
    )

    assert len(mail.outbox) == 1
    assert (
        mail.outbox[0].subject
        == f"test order approved subject, event: {order.order_number}!"
    )
    assert mail.outbox[0].body == f"{ order.order_number } { payment_url }"
    assert mail.outbox[0].to == [order.lease.application.email]

    assert mail.outbox[0].alternatives == [
        (f"<b>{ order.order_number } { payment_url }</b>", "text/html")
    ]
    assert (
        order.payment_notification_sent
        and order.payment_notification_sent <= timezone.now()
    )


@pytest.mark.parametrize(
    "order",
    ["non_billable_customer_order"],
    indirect=True,
)
def test_approve_order_with_non_billable_customer(
    order: Order,
    helsinki_profile_user,
):
    order.status = OrderStatus.DRAFTED
    order.save(update_fields=["status"])

    request = RequestFactory().request()
    due_date = today().date()
    approve_order(order, "", due_date, helsinki_profile_user, request)
    order.refresh_from_db()

    assert order.status == OrderStatus.PAID_MANUALLY
    assert len(mail.outbox) == 0


@pytest.mark.parametrize(
    "order",
    ["berth_order"],
    indirect=True,
)
def test_send_payment_notification_example_email(order: Order):
    order.customer_email = "foo@example.com"

    with pytest.raises(ValidationError) as exception:
        send_payment_notification(order, RequestFactory().request())

    assert "Missing customer email" in str(exception)


@pytest.mark.parametrize(
    "mooring_type,expected_category",
    [
        (BerthMooringType.DINGHY_PLACE, PricingCategory.DINGHY),
        (BerthMooringType.TRAWLER_PLACE, PricingCategory.TRAILER),
    ],
)
def test_get_berth_product_pricing_category_mooring_type(
    berth_order, mooring_type, expected_category
):
    berth_order.lease.berth.berth_type.mooring_type = mooring_type
    berth_order.lease.berth.berth_type.save()

    assert get_berth_product_pricing_category(berth_order) == expected_category


def test_get_berth_product_pricing_category_vasikkasaari(berth_order):
    _get_vasikkasaari_harbor.cache_clear()
    berth_order.lease.berth.berth_type.mooring_type = BerthMooringType.SIDE_SLIP_PLACE
    berth_order.lease.berth.berth_type.save()
    berth_order.lease.berth.pier.harbor.create_translation(
        "fi", name="Vasikkasaaren venesatama"
    )
    berth_order.lease.berth.pier.save()

    assert (
        get_berth_product_pricing_category(berth_order) == PricingCategory.VASIKKASAARI
    )


@pytest.mark.parametrize(
    "input, expected_output",
    [
        (DEFAULT_TAX_PERCENTAGE, "25.50"),
        (VAT_25_5, "25.50"),
        (VAT_24, "24.00"),
        (VAT_14, "14.00"),
        (VAT_10, "10.00"),
        (Decimal("0"), "0.00"),
        (Decimal("24"), "24.00"),
        (Decimal("25.5"), "25.50"),
        (Decimal("25.50"), "25.50"),
        (Decimal("1234.56789"), "1234.57"),
        (Decimal("-.555"), "-0.56"),
    ],
)
def test_tax_percentage_as_string(input: Decimal, expected_output: str):
    assert tax_percentage_as_string(input) == expected_output


@pytest.mark.parametrize(
    "tax_percentage",
    [
        VAT_24,
        "24",
        "24.0",
        "24.00",
        "24,0",
        "24,00",
        "24%",
        "24.0%",
        "24.00%",
        "24,0%",
        "24,00%",
        "  000024.000000  ",
        "   000024.00000   %  ",
        Decimal("24"),
        Decimal("24.0"),
        Decimal("24.00"),
        24,
        24.0,
    ],
)
def test_is_24_percent_true(tax_percentage):
    assert is_24_percent(tax_percentage)


@pytest.mark.parametrize(
    "tax_percentage",
    [
        None,
        True,
        False,
        "",
        " ",
        "test",
        VAT_10,
        VAT_14,
        VAT_25_5,
        "10",
        "14",
        "23.01",
        "24.",
        "24,",
        "24,01",
        "24.01",
        "23.0000000001",
        "25,5",
        "25,50",
        "25.5%",
        "25.50%",
        "25,5%",
        "25,50%",
        "  000025.50000 % ",
        Decimal("10"),
        Decimal("14"),
        Decimal("25.5"),
        Decimal("25.50"),
        10,
        14,
        25.5,
    ],
)
def test_is_24_percent_false(tax_percentage):
    assert not is_24_percent(tax_percentage)
