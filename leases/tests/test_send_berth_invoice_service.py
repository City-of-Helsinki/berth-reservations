from unittest import mock
from requests import Session

import pytest  # noqa
from anymail.exceptions import AnymailError
from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from django.core import mail
from django.test import RequestFactory
from faker import Faker
from freezegun import freeze_time

from berth_reservations.tests.factories import UserFactory
from contracts.tests.factories import BerthContractFactory
from customers.enums import InvoicingType
from customers.schema import ProfileNode
from customers.tests.conftest import mocked_response_profile
from payments.enums import OrderStatus
from payments.models import BerthProduct, Order
from payments.tests.factories import BerthProductFactory
from payments.tests.utils import get_berth_lease_pricing_category
from utils.relay import to_global_id

from ..enums import LeaseStatus
from ..models import BerthLease
from ..services import BerthInvoicingService
from ..utils import calculate_season_end_date, calculate_season_start_date
from .factories import BerthFactory, BerthLeaseFactory

faker = Faker()


def _lease_with_contract(**lease_kwargs):
    lease = BerthLeaseFactory(**lease_kwargs)
    contract = BerthContractFactory(lease=None)
    contract.lease = lease
    contract.save()
    return lease


def _send_invoices(data):
    invoicing_service = BerthInvoicingService(
        request=RequestFactory().request(), profile_token="token"
    )
    with mock.patch("customers.services.profile.requests.Session") as mock_session:
        mock_session().post.side_effect = mocked_response_profile(count=0, data=data)
        invoicing_service.send_invoices()
    return invoicing_service


@ freeze_time("2020-01-01T08:00:00Z")
@ pytest.mark.parametrize(
    "invoicing_type,sent_mail_count",
    [(InvoicingType.ONLINE_PAYMENT, 1), (InvoicingType.PAPER_INVOICE, 0)],


)
def test_send_berth_invoices_basic(
    invoicing_type, sent_mail_count, notification_template_orders_approved
):
    lease = _lease_with_contract(
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_season_start_date(today() - relativedelta(years=1)),
        end_date=calculate_season_end_date(today() - relativedelta(years=1)),
    )

    customer = lease.customer

    # Set the invoicing type
    customer.invoicing_type = invoicing_type
    customer.save()

    user = UserFactory()

    data = {
        "id": to_global_id(ProfileNode, customer.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "primary_email": {"email": user.email},
        "primary_phone": {"phone": faker.phone_number()},
    }

    assert Order.objects.count() == 0

    invoicing_service = _send_invoices(data)

    assert Order.objects.count() == 1
    assert len(invoicing_service.successful_orders) == 1
    assert len(invoicing_service.failed_orders) == 0
    assert len(invoicing_service.failed_leases) == 0

    assert Order.objects.first().id == invoicing_service.successful_orders[0]

    leases = BerthLease.objects.exclude(id=lease.id)
    assert leases.count() == 1
    lease: BerthLease = leases.first()
    assert lease.status == LeaseStatus.OFFERED
    assert lease.start_date.isoformat() == "2020-06-10"
    assert lease.end_date.isoformat() == "2020-09-14"

    orders = Order.objects.all()
    assert orders.count() == 1
    order: Order = orders.first()
    assert invoicing_service.successful_orders[0] == order.id
    assert order.lease == lease
    assert order.customer.id == customer.id
    assert order.status == OrderStatus.OFFERED

    assert len(mail.outbox) == sent_mail_count

    if sent_mail_count > 0:
        msg = mail.outbox[0]
        assert (
            msg.subject == f"test order approved subject, event: {order.order_number}!"
        )
        assert order.order_number in msg.body


@ freeze_time("2020-01-01T08:00:00Z")
def test_send_berth_invoices_no_contract(notification_template_orders_approved):
    lease = BerthLeaseFactory(
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_season_start_date(today() - relativedelta(years=1)),
        end_date=calculate_season_end_date(today() - relativedelta(years=1)),
    )

    customer = lease.customer

    BerthProductFactory(
        min_width=lease.berth.berth_type.width - 1,
        max_width=lease.berth.berth_type.width + 1,
    )

    user = UserFactory()

    data = {
        "id": to_global_id(ProfileNode, customer.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "primary_email": {"email": user.email},
        "primary_phone": {"phone": faker.phone_number()},
    }

    assert Order.objects.count() == 0

    invoicing_service = _send_invoices(data)

    assert len(invoicing_service.successful_orders) == 0
    assert len(invoicing_service.failed_orders) == 0
    assert len(invoicing_service.failed_leases) == 0
    assert Order.objects.count() == 0
    assert BerthLease.objects.count() == 1


@ freeze_time("2020-01-01T08:00:00Z")
def test_use_berth_leases_from_last_season(notification_template_orders_approved):
    # This lease from the upcoming season should be ignored
    _lease_with_contract(
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_season_start_date(today()),
        end_date=calculate_season_end_date(today()),
    )
    # Only the lease from last season will be renewed
    lease = _lease_with_contract(
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_season_start_date(today() - relativedelta(years=1)),
        end_date=calculate_season_end_date(today() - relativedelta(years=1)),
    )
    customer = lease.customer

    user = UserFactory()

    data = {
        "id": to_global_id(ProfileNode, customer.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "primary_email": {"email": user.email},
        "primary_phone": {"phone": faker.phone_number()},
    }

    assert Order.objects.count() == 0

    invoicing_service = _send_invoices(data)

    assert len(invoicing_service.successful_orders) == 1
    assert len(invoicing_service.failed_orders) == 0
    assert len(invoicing_service.failed_leases) == 0
    assert Order.objects.count() == 1

    assert Order.objects.first().id == invoicing_service.successful_orders[0]

    leases = BerthLease.objects.filter(customer=lease.customer).exclude(id=lease.id)
    assert leases.count() == 1
    lease: BerthLease = leases.first()
    assert lease.status == LeaseStatus.OFFERED
    assert lease.start_date.isoformat() == "2020-06-10"
    assert lease.end_date.isoformat() == "2020-09-14"

    orders = Order.objects.all()
    assert orders.count() == 1
    order: Order = orders.first()
    assert invoicing_service.successful_orders[0] == order.id
    assert order.lease == lease
    assert order.customer.id == customer.id
    assert order.status == OrderStatus.OFFERED

    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.subject == f"test order approved subject, event: {order.order_number}!"
    assert order.order_number in msg.body


@ freeze_time("2020-10-01T08:00:00Z")
def test_use_berth_leases_from_current_season(notification_template_orders_approved):
    # This lease from last season should be ignored
    _lease_with_contract(
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_season_start_date(today() - relativedelta(years=1)),
        end_date=calculate_season_end_date(today() - relativedelta(years=1)),
    )
    # Only the lease from the current's year season will be renewed
    lease = _lease_with_contract(
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_season_start_date(today()),
        end_date=calculate_season_end_date(today()),
    )
    customer = lease.customer

    user = UserFactory()

    data = {
        "id": to_global_id(ProfileNode, customer.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "primary_email": {"email": user.email},
        "primary_phone": {"phone": faker.phone_number()},
    }

    assert Order.objects.count() == 0

    invoicing_service = _send_invoices(data)

    assert len(invoicing_service.successful_orders) == 1
    assert len(invoicing_service.failed_orders) == 0
    assert len(invoicing_service.failed_leases) == 0
    assert Order.objects.count() == 1

    assert Order.objects.first().id == invoicing_service.successful_orders[0]

    leases = BerthLease.objects.filter(customer=lease.customer).exclude(id=lease.id)
    assert leases.count() == 1
    lease: BerthLease = leases.first()
    assert lease.status == LeaseStatus.OFFERED
    assert lease.start_date.isoformat() == "2021-06-10"
    assert lease.end_date.isoformat() == "2021-09-14"

    orders = Order.objects.all()
    assert orders.count() == 1
    order: Order = orders.first()
    assert invoicing_service.successful_orders[0] == order.id
    assert order.lease == lease
    assert order.customer.id == customer.id
    assert order.status == OrderStatus.OFFERED

    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.subject == f"test order approved subject, event: {order.order_number}!"
    assert order.order_number in msg.body


@ freeze_time("2020-01-01T08:00:00Z")
def test_berth_lease_berth_product(notification_template_orders_approved):
    lease = _lease_with_contract(
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_season_start_date(today() - relativedelta(years=1)),
        end_date=calculate_season_end_date(today() - relativedelta(years=1)),
    )
    customer = lease.customer

    user = UserFactory()

    data = {
        "id": to_global_id(ProfileNode, customer.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "primary_email": {"email": user.email},
        "primary_phone": {"phone": faker.phone_number()},
    }

    assert Order.objects.count() == 0

    invoicing_service = _send_invoices(data)

    assert len(invoicing_service.successful_orders) == 1
    assert len(invoicing_service.failed_orders) == 0
    assert len(invoicing_service.failed_leases) == 0
    assert Order.objects.count() == 1

    order = Order.objects.first()
    assert order.id == invoicing_service.successful_orders[0]
    assert isinstance(order.product, BerthProduct)


@ freeze_time("2020-01-01T08:00:00Z")
def test_berth_lease_no_product():
    lease = _lease_with_contract(
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_season_start_date(today() - relativedelta(years=1)),
        end_date=calculate_season_end_date(today() - relativedelta(years=1)),
        create_product=False,
    )
    customer = lease.customer

    user = UserFactory()

    data = {
        "id": to_global_id(ProfileNode, customer.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "primary_email": {"email": user.email},
        "primary_phone": {"phone": faker.phone_number()},
    }

    assert Order.objects.count() == 0

    invoicing_service = _send_invoices(data)

    assert len(invoicing_service.successful_orders) == 0
    assert len(invoicing_service.failed_orders) == 0
    assert len(invoicing_service.failed_leases) == 1
    assert Order.objects.count() == 0
    assert BerthLease.objects.count() == 2

    lease = BerthLease.objects.exclude(id=lease.id).first()
    assert lease.id in invoicing_service.failed_leases[0].keys()
    assert (
        "Order must have either product object or price value"
        in invoicing_service.failed_leases[0].get(lease.id)
    )


@ freeze_time("2020-01-01T08:00:00Z")
def test_send_berth_invoices_missing_email(notification_template_orders_approved):
    lease = _lease_with_contract(
        boat=None,
        status=LeaseStatus.PAID,
        start_date=today() - relativedelta(years=1),
        end_date=today() + relativedelta(years=-1, months=5),
    )
    customer = lease.customer

    user = UserFactory()

    data = {
        "id": to_global_id(ProfileNode, customer.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "primary_email": None,
        "primary_phone": None,
    }

    assert Order.objects.count() == 0

    invoicing_service = _send_invoices(data)

    assert len(invoicing_service.successful_orders) == 0
    assert len(invoicing_service.failed_orders) == 1
    assert len(invoicing_service.failed_leases) == 1  # both order and lease fail
    assert Order.objects.count() == 1

    order = Order.objects.first()

    assert order.status == OrderStatus.ERROR
    assert order.comment == "01-01-2020 10:00:00: Missing customer email"
    assert order.id in invoicing_service.failed_orders[0].keys()
    assert order.due_date is None
    assert invoicing_service.failed_orders[0].get(order.id) == "Missing customer email"

    assert len(mail.outbox) == 0

    leases = BerthLease.objects.exclude(id=lease.id)
    assert leases.count() == 1
    lease: BerthLease = leases.first()
    assert lease.status == LeaseStatus.ERROR
    assert "Error with the order, check the order first" in lease.comment
    assert lease.start_date.isoformat() == "2020-06-10"
    assert lease.end_date.isoformat() == "2020-09-14"


@ freeze_time("2020-01-01T08:00:00Z")
def test_send_berth_invoices_invalid_example_email(
    notification_template_orders_approved,
):
    lease = _lease_with_contract(
        boat=None,
        status=LeaseStatus.PAID,
        start_date=today() - relativedelta(years=1),
        end_date=today() + relativedelta(years=-1, months=5),
    )
    customer = lease.customer

    user = UserFactory()

    data = {
        "id": to_global_id(ProfileNode, customer.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "primary_email": {"email": "something@example.com"},
        "primary_phone": {"phone": faker.phone_number()},
    }

    assert Order.objects.count() == 0

    invoicing_service = _send_invoices(data)

    assert len(invoicing_service.successful_orders) == 0
    assert len(invoicing_service.failed_orders) == 1
    assert len(invoicing_service.failed_leases) == 1  # both order and lease fail
    assert Order.objects.count() == 1

    order = Order.objects.first()

    assert order.status == OrderStatus.ERROR
    assert order.comment == "01-01-2020 10:00:00: Missing customer email"
    assert order.id in invoicing_service.failed_orders[0].keys()
    assert order.due_date is None
    assert invoicing_service.failed_orders[0].get(order.id) == "Missing customer email"

    assert len(mail.outbox) == 0

    leases = BerthLease.objects.exclude(id=lease.id)
    assert leases.count() == 1
    lease: BerthLease = leases.first()
    assert lease.status == LeaseStatus.ERROR
    assert "Error with the order, check the order first" in lease.comment
    assert lease.start_date.isoformat() == "2020-06-10"
    assert lease.end_date.isoformat() == "2020-09-14"


@ freeze_time("2020-01-01T08:00:00Z")
def test_send_berth_invoices_send_error(notification_template_orders_approved):
    lease = _lease_with_contract(
        boat=None,
        status=LeaseStatus.PAID,
        start_date=today() - relativedelta(years=1),
        end_date=today() + relativedelta(years=-1, months=5),
    )
    customer = lease.customer

    user = UserFactory()

    data = {
        "id": to_global_id(ProfileNode, customer.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "primary_email": {"email": user.email},
        "primary_phone": {"phone": faker.phone_number()},
    }

    assert Order.objects.count() == 0

    with mock.patch.object(Session,
                           "post",
                           side_effect=mocked_response_profile(count=0, data=data),
                           ):
        with mock.patch(
            "payments.utils.send_notification",
            side_effect=AnymailError("Anymail error"),
        ):
            invoicing_service = BerthInvoicingService(
                request=RequestFactory().request(), profile_token="token"
            )
            invoicing_service.send_invoices()

    assert len(invoicing_service.successful_orders) == 0
    assert len(invoicing_service.failed_orders) == 1
    assert len(invoicing_service.failed_leases) == 0
    assert Order.objects.count() == 1

    order = Order.objects.first()

    assert order.id in invoicing_service.failed_orders[0].keys()
    assert order.comment == "01-01-2020 10:00:00: Anymail error"
    assert order.due_date is None
    assert invoicing_service.failed_orders[0].get(order.id) == "Anymail error"

    assert len(mail.outbox) == 0

    leases = BerthLease.objects.exclude(id=lease.id)
    assert leases.count() == 1
    lease: BerthLease = leases.first()
    assert lease.status == LeaseStatus.ERROR
    assert "Error with the order, check the order first" in lease.comment
    assert lease.start_date.isoformat() == "2020-06-10"
    assert lease.end_date.isoformat() == "2020-09-14"

    assert order.status == OrderStatus.ERROR
    assert (
        order.log_entries.get(to_status=OrderStatus.ERROR).comment
        == "Lease renewing failed: Anymail error"
    )


@ freeze_time("2020-01-01T08:00:00Z")
def test_send_berth_invoices_only_not_renewed(notification_template_orders_approved):
    # This lease should be ignored since it already has a lease for the upcoming season
    renewed_lease = _lease_with_contract(
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_season_start_date(today() - relativedelta(years=1)),
        end_date=calculate_season_end_date(today() - relativedelta(years=1)),
    )
    # Renewed lease for the previous one
    _lease_with_contract(
        customer=renewed_lease.customer,
        berth=renewed_lease.berth,
        boat=None,
        status=LeaseStatus.DRAFTED,
        start_date=calculate_season_start_date(today()),
        end_date=calculate_season_end_date(today()),
    )
    # This lease should be renewed
    valid_lease = _lease_with_contract(
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_season_start_date(today() - relativedelta(years=1)),
        end_date=calculate_season_end_date(today() - relativedelta(years=1)),
    )

    customer = valid_lease.customer

    user = UserFactory()

    data = {
        "id": to_global_id(ProfileNode, customer.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "primary_email": {"email": user.email},
        "primary_phone": {"phone": faker.phone_number()},
    }

    assert Order.objects.count() == 0

    invoicing_service = _send_invoices(data)

    assert len(invoicing_service.successful_orders) == 1
    assert len(invoicing_service.failed_orders) == 0
    assert len(invoicing_service.failed_leases) == 0
    assert Order.objects.count() == 1

    assert Order.objects.first().id == invoicing_service.successful_orders[0]

    # The already renewed lease and the old one, plus the valid and it's renewed lease
    assert BerthLease.objects.count() == 4
    lease: BerthLease = (
        BerthLease.objects.filter(customer=valid_lease.customer)
        .exclude(id=valid_lease.id)
        .first()
    )

    assert lease.status == LeaseStatus.OFFERED
    assert lease.start_date.isoformat() == "2020-06-10"
    assert lease.end_date.isoformat() == "2020-09-14"

    orders = Order.objects.all()
    assert orders.count() == 1
    order: Order = orders.first()
    assert invoicing_service.successful_orders[0] == order.id
    assert order.lease == lease
    assert order.customer.id == customer.id
    assert order.status == OrderStatus.OFFERED


@ freeze_time("2020-01-01T08:00:00Z")
def test_send_berth_invoices_invalid_limit_reached(
    notification_template_orders_approved,
):
    first_lease = _lease_with_contract(
        boat=None,
        status=LeaseStatus.PAID,
        start_date=today() - relativedelta(years=1),
        end_date=today() + relativedelta(years=-1, months=5),
    )
    for _ in range(2):
        _lease_with_contract(
            boat=None,
            status=LeaseStatus.PAID,
            start_date=today() - relativedelta(years=1),
            end_date=today() + relativedelta(years=-1, months=5),
        )
    customer = first_lease.customer
    BerthProductFactory(
        min_width=first_lease.berth.berth_type.width - 1,
        max_width=first_lease.berth.berth_type.width + 1,
    )

    user = UserFactory()

    data = {
        "id": to_global_id(ProfileNode, customer.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "primary_email": {"email": "something@example.com"},
        "primary_phone": {"phone": faker.phone_number()},
    }

    assert Order.objects.count() == 0
    invoicing_service = BerthInvoicingService(
        request=RequestFactory().request(), profile_token="token"
    )
    with mock.patch.object(Session,
                           "post",
                           side_effect=mocked_response_profile(count=1, data=data),
                           ):
        with mock.patch.object(
            invoicing_service,
            "email_admins",
            wraps=invoicing_service.email_admins,
        ) as email_admins_mock:
            invoicing_service.MAXIMUM_FAILURES = 1
            invoicing_service.send_invoices()
            email_admins_mock.assert_called_once_with(
                True
            )  # called with exited_with_errors=True
            assert invoicing_service.failure_count == 1


@ freeze_time("2020-01-01T08:00:00Z")
def test_non_invoiceable_berth(notification_template_orders_approved):
    berth = BerthFactory(is_invoiceable=False)

    lease_with_non_invoiceable_berth = _lease_with_contract(
        berth=berth,
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_season_start_date(today() - relativedelta(years=1)),
        end_date=calculate_season_end_date(today() - relativedelta(years=1)),
    )
    customer = lease_with_non_invoiceable_berth.customer

    lease_with_invoiceable_berth = _lease_with_contract(
        customer=customer,
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_season_start_date(today() - relativedelta(years=1)),
        end_date=calculate_season_end_date(today() - relativedelta(years=1)),
    )
    expected_product = BerthProduct.objects.get_in_range(
        lease_with_invoiceable_berth.berth.berth_type.width,
        get_berth_lease_pricing_category(lease_with_invoiceable_berth),
    )

    user = UserFactory()

    data = {
        "id": to_global_id(ProfileNode, customer.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "primary_email": {"email": user.email},
        "primary_phone": {"phone": faker.phone_number()},
    }

    assert Order.objects.count() == 0

    invoicing_service = _send_invoices(data)

    assert len(invoicing_service.successful_orders) == 1
    assert len(invoicing_service.failed_orders) == 0
    assert len(invoicing_service.failed_leases) == 0
    assert Order.objects.count() == 1

    order = Order.objects.first()
    assert order.id == invoicing_service.successful_orders[0]
    assert order.product == expected_product
