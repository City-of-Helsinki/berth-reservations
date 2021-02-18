from decimal import Decimal
from typing import Dict, List

import factory
from dateutil.utils import today
from django.conf import settings
from django_ilmoitin.dummy_context import dummy_context

from berth_reservations.tests.factories import CustomerProfileFactory
from leases.tests.factories import BerthLeaseFactory, WinterStorageLeaseFactory

from ..enums import OrderStatus, ProductServiceType
from ..models import Order, OrderLine
from ..providers import BamboraPayformProvider
from ..tests.factories import (
    BerthProductFactory,
    OrderFactory,
    OrderLineFactory,
    WinterStorageProductFactory,
)
from ..tests.utils import random_price
from ..utils import get_email_subject
from .types import NotificationType

provider = BamboraPayformProvider(
    config={
        "VENE_PAYMENTS_BAMBORA_API_URL": "https://real-bambora-api-url/api",
        "VENE_PAYMENTS_BAMBORA_API_KEY": "dummy-key",
        "VENE_PAYMENTS_BAMBORA_API_SECRET": "dummy-secret",
        "VENE_PAYMENTS_BAMBORA_PAYMENT_METHODS": ["dummy-bank"],
    },
    ui_return_url=settings.VENE_UI_RETURN_URL,
)


def _get_order_context(
    subject: str, order: Order, optional_services: List[OrderLine],
) -> Dict:
    return {
        "subject": subject,
        "order": order,
        "payment_url": provider.get_payment_email_url(order, settings.LANGUAGE_CODE),
        "cancel_url": provider.get_cancellation_email_url(
            order, settings.LANGUAGE_CODE
        ),
        "optional_services": optional_services,
    }


def _get_berth_order_context(subject: str = "Berth order"):
    customer = CustomerProfileFactory.build()
    order = OrderFactory.build(
        customer=customer,
        product=BerthProductFactory.build(),
        lease=BerthLeaseFactory.build(
            customer=customer,
            # Fixed to a harbor with a real image
            berth__pier__harbor__image_file="/img/helsinki_harbors/41189.jpg",
        ),
        price=Decimal("100"),
        tax_percentage=Decimal("24.00"),
    )
    optional_services = [
        OrderLineFactory.build(
            order=order,
            product__service=ProductServiceType.OPTIONAL_SERVICES()[0],
            price=random_price(),
        ),
        OrderLineFactory.build(
            order=order,
            product__service=ProductServiceType.OPTIONAL_SERVICES()[1],
            price=random_price(),
        ),
    ]

    return _get_order_context(subject, order, optional_services)


def _get_winter_storage_order_context(subject: str = "Winter storage order"):
    customer = CustomerProfileFactory.build()
    order = OrderFactory.build(
        customer=customer,
        product=WinterStorageProductFactory.build(),
        lease=WinterStorageLeaseFactory.build(customer=customer),
        price=Decimal("100"),
        tax_percentage=Decimal("24.00"),
    )
    optional_services = [
        OrderLineFactory.build(
            order=order,
            product__service=ProductServiceType.OPTIONAL_SERVICES()[0],
            price=random_price(),
        ),
        OrderLineFactory.build(
            order=order,
            product__service=ProductServiceType.OPTIONAL_SERVICES()[1],
            price=random_price(),
        ),
    ]

    return _get_order_context(subject, order, optional_services)


def _get_additional_product_order_context(subject: str = "Additional product order"):
    return {
        "subject": subject,
        "order": {
            "lease": {
                "start_date": today().date(),
                "end_date": today().date(),
                "berth": {"pier": {"harbor": {"name": "Satama"}}},
            },
            "total_price": Decimal("100.00"),
            "due_date": today().date(),
        },
        "additional_product": {"name": "Product name", "season": "2020 - 2021"},
        "payment_url": "http://foo.com",
    }


def _get_cancelled_order_context(subject: str = "Order cancelled"):
    customer = CustomerProfileFactory.build()
    # The rejected_at field relies on an annotated field from the database, so since we can't
    # query here as the objects are not saved on the db, we manually add the rejected_at.

    return {
        "subject": subject,
        "order": {
            **factory.build(
                dict,
                FACTORY_CLASS=OrderFactory,
                customer=customer,
                status=OrderStatus.WAITING,
                product=BerthProductFactory.build(),
                lease=BerthLeaseFactory.build(customer=customer),
                price=Decimal("100"),
                tax_percentage=Decimal("24.00"),
            ),
            "rejected_at": today().date(),
        },
    }


def load_dummy_context():
    dummy_context.update(
        {
            NotificationType.NEW_BERTH_ORDER_APPROVED: _get_berth_order_context(
                get_email_subject(NotificationType.NEW_BERTH_ORDER_APPROVED)
            ),
            NotificationType.RENEW_BERTH_ORDER_APPROVED: _get_berth_order_context(
                get_email_subject(NotificationType.RENEW_BERTH_ORDER_APPROVED)
            ),
            NotificationType.BERTH_SWITCH_ORDER_APPROVED: _get_berth_order_context(
                get_email_subject(NotificationType.BERTH_SWITCH_ORDER_APPROVED)
            ),
            NotificationType.NEW_WINTER_STORAGE_ORDER_APPROVED: _get_winter_storage_order_context(
                get_email_subject(NotificationType.NEW_WINTER_STORAGE_ORDER_APPROVED)
            ),
            NotificationType.UNMARKED_WINTER_STORAGE_ORDER_APPROVED: _get_winter_storage_order_context(
                get_email_subject(
                    NotificationType.UNMARKED_WINTER_STORAGE_ORDER_APPROVED
                )
            ),
            NotificationType.ADDITIONAL_PRODUCT_ORDER_APPROVED: _get_additional_product_order_context(
                get_email_subject(NotificationType.ADDITIONAL_PRODUCT_ORDER_APPROVED)
            ),
            NotificationType.ORDER_CANCELLED: _get_cancelled_order_context(
                get_email_subject(NotificationType.ORDER_CANCELLED)
            ),
            NotificationType.SMS_INVOICE_NOTICE: {
                "product_name": "Berth",
                "due_date": str(today()),
                "payment_url": "https://foo.bar/payment",
            },
        }
    )
