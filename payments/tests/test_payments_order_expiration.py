import datetime

import pytest  # noqa
from django.core.exceptions import ValidationError
from freezegun import freeze_time

from applications.enums import ApplicationStatus
from customers.enums import InvoicingType
from leases.enums import LeaseStatus
from payments.enums import OrderStatus
from payments.models import Order
from payments.tests.factories import OrderFactory


@freeze_time("2021-01-09T08:00:00Z")
@pytest.mark.parametrize("berth_application", ["base", "switch"], indirect=True)
def test_expire_too_old_unpaid_orders(
    berth_application, berth_lease, berth_lease_without_product
):
    # VEN-783:
    # The due date should only be editable up to 7 days after it has expired.
    # Therefore invalidated orders should be expired when due date + 7 days have gone.
    berth_lease.application = berth_application
    berth_lease.save()

    # Create and order for a digital invoice customer (default)
    order = OrderFactory(
        lease=berth_lease,
        customer=berth_lease.customer,
        due_date=datetime.date(2021, 1, 2),  # unexpired
        status=OrderStatus.OFFERED,
    )

    # Create an order for a paper invoice customer
    berth_lease_without_product.customer.invoicing_type = InvoicingType.PAPER_INVOICE
    berth_lease_without_product.customer.save()
    OrderFactory(
        lease=berth_lease_without_product,
        price="9.99",
        tax_percentage="14.0",
        due_date=datetime.date(2021, 1, 1),  # expired
        status=OrderStatus.OFFERED,
        customer=berth_lease_without_product.customer,
    )

    # dry run: test that the paper invoice customers are included but the unexpired aren't
    assert (
        Order.objects.expire_too_old_unpaid_orders(older_than_days=7, dry_run=True) == 1
    )
    # real run: test that the paper invoice customers are excluded
    assert (
        Order.objects.expire_too_old_unpaid_orders(
            older_than_days=7, dry_run=False, exclude_paper_invoice_customers=True
        )
        == 0
    )
    order.refresh_from_db()
    assert order.status == OrderStatus.OFFERED

    # Update the order to be expired
    order.due_date = datetime.date(2021, 1, 1)
    order.save()

    assert (
        Order.objects.expire_too_old_unpaid_orders(older_than_days=7, dry_run=False)
        == 2
    )

    order.refresh_from_db()
    order.lease.refresh_from_db()
    assert order.status == OrderStatus.EXPIRED
    assert order.lease.status == LeaseStatus.EXPIRED
    assert order.lease.application.status == ApplicationStatus.EXPIRED
    assert len(order.log_entries.all()) == 1
    assert "Order expired at 2021-01-02" in order.log_entries.first().comment
    # VEN-783: "After that, it should not be possible to modify, and the API should return an error."
    order.due_date = datetime.datetime(2021, 2, 1)
    with pytest.raises(ValidationError):
        order.save()
