from decimal import Decimal

from django.conf import settings
from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _
from django_ilmoitin.dummy_context import dummy_context
from django_ilmoitin.registry import notifications

from berth_reservations.tests.factories import CustomerProfileFactory

from .providers import BamboraPayformProvider
from .tests.conftest import PROVIDER_BASE_CONFIG
from .tests.factories import OrderFactory


class NotificationType(TextChoices):
    ORDER_APPROVED = (
        "order_approved",
        _("Order approved"),
    )


notifications.register(
    NotificationType.ORDER_APPROVED.value, NotificationType.ORDER_APPROVED.label,
)

customer = CustomerProfileFactory.build()
order = OrderFactory.build(
    customer=customer,
    product=None,
    price=Decimal("100"),
    tax_percentage=Decimal("24.00"),
)


payment_url = BamboraPayformProvider(
    config=PROVIDER_BASE_CONFIG, ui_return_url=settings.VENE_UI_RETURN_URL
).get_payment_email_url(order, lang=settings.LANGUAGE_CODE)

dummy_context.update(
    {NotificationType.ORDER_APPROVED: {"order": order, "payment_url": payment_url}}
)
