import datetime

from django.core.management import call_command
from django.test import TestCase
from freezegun import freeze_time

from berth_reservations.tests.factories import CustomerProfileFactory
from customers.enums import InvoicingType
from payments.enums import OrderStatus
from payments.models import Order
from payments.tests.factories import OrderFactory


@freeze_time("2021-01-09T08:00:00Z")
class CommandsTestCase(TestCase):
    def setUp(self) -> None:
        digital_customer = CustomerProfileFactory(
            invoicing_type=InvoicingType.ONLINE_PAYMENT
        )
        paper_customer = CustomerProfileFactory(
            invoicing_type=InvoicingType.PAPER_INVOICE
        )
        OrderFactory(
            customer=digital_customer,
            status=OrderStatus.OFFERED,
            due_date=datetime.date(2021, 1, 1),
        )
        OrderFactory(
            customer=paper_customer,
            status=OrderStatus.OFFERED,
            due_date=datetime.date(2021, 1, 1),
        )

        assert Order.objects.filter(status=OrderStatus.OFFERED).count() == 2

    def test_expire_too_old_unpaid_orders(self):
        args = []
        opts = {}
        call_command("expire_too_old_unpaid_orders", *args, **opts)
        Order.objects.filter(status=OrderStatus.OFFERED).count() == 1
        # Paper invoice customers should be excluded by default and they should be left untouched
        Order.objects.filter(
            customer__invoicing_type=InvoicingType.PAPER_INVOICE
        ).count() == 1

    def test_expire_too_old_unpaid_orders_exclude_paper_invoice_customers(self):
        args = []
        opts = {"include_paper_invoice_customers": True}
        call_command("expire_too_old_unpaid_orders", *args, **opts)
        Order.objects.filter(status=OrderStatus.OFFERED).count() == 0

    def test_expire_too_old_unpaid_orders_dry_run(self):
        args = []
        opts = {"dry_run": True}
        call_command("expire_too_old_unpaid_orders", *args, **opts)
        Order.objects.filter(status=OrderStatus.OFFERED).count() == 2
