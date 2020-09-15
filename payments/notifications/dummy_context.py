from decimal import Decimal

from django.conf import settings
from django_ilmoitin.dummy_context import dummy_context

from berth_reservations.tests.factories import CustomerProfileFactory
from leases.tests.factories import BerthLeaseFactory

from ..enums import ProductServiceType
from ..providers import BamboraPayformProvider
from ..tests.factories import BerthProductFactory, OrderFactory, OrderLineFactory
from .types import NotificationType


def load_dummy_context():
    customer = CustomerProfileFactory.build()
    order = OrderFactory.build(
        customer=customer,
        product=BerthProductFactory.build(),
        lease=BerthLeaseFactory.build(customer=customer),
        price=Decimal("100"),
        tax_percentage=Decimal("24.00"),
    )
    fixed_services = [
        OrderLineFactory.build(
            order=order, product__service=ProductServiceType.FIXED_SERVICES()[0]
        ),
        OrderLineFactory.build(
            order=order, product__service=ProductServiceType.FIXED_SERVICES()[1]
        ),
        OrderLineFactory.build(
            order=order, product__service=ProductServiceType.FIXED_SERVICES()[2]
        ),
        OrderLineFactory.build(
            order=order, product__service=ProductServiceType.FIXED_SERVICES()[3]
        ),
    ]
    optional_services = [
        OrderLineFactory.build(
            order=order, product__service=ProductServiceType.OPTIONAL_SERVICES()[0]
        ),
        OrderLineFactory.build(
            order=order, product__service=ProductServiceType.OPTIONAL_SERVICES()[1]
        ),
    ]

    payment_url = BamboraPayformProvider(
        config={
            "VENE_PAYMENTS_BAMBORA_API_URL": "https://real-bambora-api-url/api",
            "VENE_PAYMENTS_BAMBORA_API_KEY": "dummy-key",
            "VENE_PAYMENTS_BAMBORA_API_SECRET": "dummy-secret",
            "VENE_PAYMENTS_BAMBORA_PAYMENT_METHODS": ["dummy-bank"],
        },
        ui_return_url=settings.VENE_UI_RETURN_URL,
    ).get_payment_email_url(order, lang=settings.LANGUAGE_CODE)

    dummy_context.update(
        {
            NotificationType.ORDER_APPROVED: {
                "order": order,
                "payment_url": payment_url,
                "fixed_services": fixed_services,
                "optional_services": optional_services,
            }
        }
    )
