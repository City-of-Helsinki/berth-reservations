from typing import Dict, List
from unittest import mock
from uuid import UUID

import pytest  # noqa
from anymail.exceptions import AnymailError
from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from django.core import mail
from django.test import RequestFactory
from freezegun import freeze_time

from berth_reservations.tests.factories import UserFactory
from customers.schema import ProfileNode
from customers.tests.conftest import mocked_response_profile
from leases.enums import LeaseStatus
from leases.models import BerthLease
from leases.tasks import send_berth_invoices
from leases.tests.factories import BerthLeaseFactory
from leases.utils import calculate_season_end_date, calculate_season_start_date
from payments.enums import OrderStatus
from payments.models import BerthPriceGroup, Order
from payments.tests.factories import BerthProductFactory
from utils.relay import to_global_id

PROFILE_TOKEN_SERVICE = "http://fake-profile-api.com"


@freeze_time("2020-01-01T08:00:00Z")
def test_send_berth_invoices(notification_template_orders_approved):
    lease = BerthLeaseFactory(
        renew_automatically=True,
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_season_start_date(today() - relativedelta(years=1)),
        end_date=calculate_season_end_date(today() - relativedelta(years=1)),
    )
    customer = lease.customer
    price_group = BerthPriceGroup.objects.get_or_create_for_width(
        lease.berth.berth_type.width
    )
    BerthProductFactory(price_group=price_group, harbor=lease.berth.pier.harbor)

    user = UserFactory()

    r = RequestFactory().request(
        HTTP_API_TOKENS=f'{{"{PROFILE_TOKEN_SERVICE}": "token"}}'
    )
    data = {
        "id": to_global_id(ProfileNode, customer.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "primary_email": {"email": user.email},
    }

    assert Order.objects.count() == 0

    with mock.patch(
        "customers.services.profile.requests.post",
        side_effect=mocked_response_profile(count=0, data=data),
    ):
        result = send_berth_invoices(r)

    successful_orders: List[UUID] = result.get("successful_orders")
    failed_orders: List[Dict[UUID, str]] = result.get("failed_orders")
    failed_leases: List[Dict[UUID, str]] = result.get("failed_leases")

    assert len(successful_orders) == 1
    assert len(failed_orders) == 0
    assert len(failed_leases) == 0
    assert Order.objects.count() == 1

    assert Order.objects.first().id == successful_orders[0]

    leases = BerthLease.objects.exclude(id=lease.id)
    assert leases.count() == 1
    lease: BerthLease = leases.first()
    assert lease.status == LeaseStatus.OFFERED
    assert lease.start_date.isoformat() == "2020-06-10"
    assert lease.end_date.isoformat() == "2020-09-14"

    orders = Order.objects.all()
    assert orders.count() == 1
    order: Order = orders.first()
    assert successful_orders[0] == order.id
    assert order.lease == lease
    assert order.customer.id == customer.id
    assert order.status == OrderStatus.WAITING

    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.subject == f"test order approved subject, event: { order.order_number }!"
    assert order.order_number in msg.body


@freeze_time("2020-01-01T08:00:00Z")
def test_use_berth_leases_from_last_season(notification_template_orders_approved):
    # This lease from the upcoming season should be ignored
    BerthLeaseFactory(
        renew_automatically=True,
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_season_start_date(today()),
        end_date=calculate_season_end_date(today()),
    )
    # Only the lease from last season will be renewed
    lease = BerthLeaseFactory(
        renew_automatically=True,
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_season_start_date(today() - relativedelta(years=1)),
        end_date=calculate_season_end_date(today() - relativedelta(years=1)),
    )
    customer = lease.customer
    price_group = BerthPriceGroup.objects.get_or_create_for_width(
        lease.berth.berth_type.width
    )
    BerthProductFactory(price_group=price_group, harbor=lease.berth.pier.harbor)

    user = UserFactory()

    r = RequestFactory().request(
        HTTP_API_TOKENS=f'{{"{PROFILE_TOKEN_SERVICE}": "token"}}'
    )
    data = {
        "id": to_global_id(ProfileNode, customer.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "primary_email": {"email": user.email},
    }

    assert Order.objects.count() == 0

    with mock.patch(
        "customers.services.profile.requests.post",
        side_effect=mocked_response_profile(count=0, data=data),
    ):
        result = send_berth_invoices(r)

    successful_orders: List[UUID] = result.get("successful_orders")
    failed_orders: List[Dict[UUID, str]] = result.get("failed_orders")
    failed_leases: List[Dict[UUID, str]] = result.get("failed_leases")

    assert len(successful_orders) == 1
    assert len(failed_orders) == 0
    assert len(failed_leases) == 0
    assert Order.objects.count() == 1

    assert Order.objects.first().id == successful_orders[0]

    leases = BerthLease.objects.filter(customer=lease.customer).exclude(id=lease.id)
    assert leases.count() == 1
    lease: BerthLease = leases.first()
    assert lease.status == LeaseStatus.OFFERED
    assert lease.start_date.isoformat() == "2020-06-10"
    assert lease.end_date.isoformat() == "2020-09-14"

    orders = Order.objects.all()
    assert orders.count() == 1
    order: Order = orders.first()
    assert successful_orders[0] == order.id
    assert order.lease == lease
    assert order.customer.id == customer.id
    assert order.status == OrderStatus.WAITING

    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.subject == f"test order approved subject, event: { order.order_number }!"
    assert order.order_number in msg.body


@freeze_time("2020-10-01T08:00:00Z")
def test_use_berth_leases_from_current_season(notification_template_orders_approved):
    # This lease from last season should be ignored
    BerthLeaseFactory(
        renew_automatically=True,
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_season_start_date(today() - relativedelta(years=1)),
        end_date=calculate_season_end_date(today() - relativedelta(years=1)),
    )
    # Only the lease from the current's year season will be renewed
    lease = BerthLeaseFactory(
        renew_automatically=True,
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_season_start_date(today()),
        end_date=calculate_season_end_date(today()),
    )
    customer = lease.customer
    price_group = BerthPriceGroup.objects.get_or_create_for_width(
        lease.berth.berth_type.width
    )
    BerthProductFactory(price_group=price_group, harbor=lease.berth.pier.harbor)

    user = UserFactory()

    r = RequestFactory().request(
        HTTP_API_TOKENS=f'{{"{PROFILE_TOKEN_SERVICE}": "token"}}'
    )
    data = {
        "id": to_global_id(ProfileNode, customer.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "primary_email": {"email": user.email},
    }

    assert Order.objects.count() == 0

    with mock.patch(
        "customers.services.profile.requests.post",
        side_effect=mocked_response_profile(count=0, data=data),
    ):
        result = send_berth_invoices(r)

    successful_orders: List[UUID] = result.get("successful_orders")
    failed_orders: List[Dict[UUID, str]] = result.get("failed_orders")
    failed_leases: List[Dict[UUID, str]] = result.get("failed_leases")

    assert len(successful_orders) == 1
    assert len(failed_orders) == 0
    assert len(failed_leases) == 0
    assert Order.objects.count() == 1

    assert Order.objects.first().id == successful_orders[0]

    leases = BerthLease.objects.filter(customer=lease.customer).exclude(id=lease.id)
    assert leases.count() == 1
    lease: BerthLease = leases.first()
    assert lease.status == LeaseStatus.OFFERED
    assert lease.start_date.isoformat() == "2021-06-10"
    assert lease.end_date.isoformat() == "2021-09-14"

    orders = Order.objects.all()
    assert orders.count() == 1
    order: Order = orders.first()
    assert successful_orders[0] == order.id
    assert order.lease == lease
    assert order.customer.id == customer.id
    assert order.status == OrderStatus.WAITING

    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.subject == f"test order approved subject, event: { order.order_number }!"
    assert order.order_number in msg.body


@freeze_time("2020-01-01T08:00:00Z")
def test_berth_lease_harbor_product(notification_template_orders_approved):
    lease = BerthLeaseFactory(
        renew_automatically=True,
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_season_start_date(today() - relativedelta(years=1)),
        end_date=calculate_season_end_date(today() - relativedelta(years=1)),
    )
    customer = lease.customer
    price_group = BerthPriceGroup.objects.get_or_create_for_width(
        lease.berth.berth_type.width
    )
    BerthProductFactory(price_group=price_group, harbor=lease.berth.pier.harbor)

    user = UserFactory()

    r = RequestFactory().request(
        HTTP_API_TOKENS=f'{{"{PROFILE_TOKEN_SERVICE}": "token"}}'
    )
    data = {
        "id": to_global_id(ProfileNode, customer.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "primary_email": {"email": user.email},
    }

    assert Order.objects.count() == 0

    with mock.patch(
        "customers.services.profile.requests.post",
        side_effect=mocked_response_profile(count=0, data=data),
    ):
        result = send_berth_invoices(r)

    successful_orders: List[UUID] = result.get("successful_orders")
    failed_orders: List[Dict[UUID, str]] = result.get("failed_orders")
    failed_leases: List[Dict[UUID, str]] = result.get("failed_leases")

    assert len(successful_orders) == 1
    assert len(failed_orders) == 0
    assert len(failed_leases) == 0
    assert Order.objects.count() == 1

    order = Order.objects.first()
    assert order.id == successful_orders[0]
    assert order.product.harbor == order.lease.berth.pier.harbor


@freeze_time("2020-01-01T08:00:00Z")
def test_berth_lease_default_product(notification_template_orders_approved):
    lease = BerthLeaseFactory(
        renew_automatically=True,
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_season_start_date(today() - relativedelta(years=1)),
        end_date=calculate_season_end_date(today() - relativedelta(years=1)),
    )
    customer = lease.customer
    price_group = BerthPriceGroup.objects.get_or_create_for_width(
        lease.berth.berth_type.width
    )
    BerthProductFactory(price_group=price_group, harbor=None)

    user = UserFactory()

    r = RequestFactory().request(
        HTTP_API_TOKENS=f'{{"{PROFILE_TOKEN_SERVICE}": "token"}}'
    )
    data = {
        "id": to_global_id(ProfileNode, customer.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "primary_email": {"email": user.email},
    }

    assert Order.objects.count() == 0

    with mock.patch(
        "customers.services.profile.requests.post",
        side_effect=mocked_response_profile(count=0, data=data),
    ):
        result = send_berth_invoices(r)

    successful_orders: List[UUID] = result.get("successful_orders")
    failed_orders: List[Dict[UUID, str]] = result.get("failed_orders")
    failed_leases: List[Dict[UUID, str]] = result.get("failed_leases")

    assert len(successful_orders) == 1
    assert len(failed_orders) == 0
    assert len(failed_leases) == 0
    assert Order.objects.count() == 1

    order = Order.objects.first()
    assert order.id == successful_orders[0]
    assert order.product.harbor is None


@freeze_time("2020-01-01T08:00:00Z")
def test_berth_lease_no_product():
    lease = BerthLeaseFactory(
        renew_automatically=True,
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_season_start_date(today() - relativedelta(years=1)),
        end_date=calculate_season_end_date(today() - relativedelta(years=1)),
    )
    customer = lease.customer

    user = UserFactory()

    r = RequestFactory().request(
        HTTP_API_TOKENS=f'{{"{PROFILE_TOKEN_SERVICE}": "token"}}'
    )
    data = {
        "id": to_global_id(ProfileNode, customer.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "primary_email": {"email": user.email},
    }

    assert Order.objects.count() == 0

    with mock.patch(
        "customers.services.profile.requests.post",
        side_effect=mocked_response_profile(count=0, data=data),
    ):
        result = send_berth_invoices(r)

    successful_orders: List[UUID] = result.get("successful_orders")
    failed_orders: List[Dict[UUID, str]] = result.get("failed_orders")
    failed_leases: List[Dict[UUID, str]] = result.get("failed_leases")

    assert len(successful_orders) == 0
    assert len(failed_orders) == 0
    assert len(failed_leases) == 1
    assert Order.objects.count() == 0
    assert BerthLease.objects.count() == 2

    lease = BerthLease.objects.exclude(id=lease.id).first()
    assert lease.id in failed_leases[0].keys()
    assert failed_leases[0].get(lease.id) == "No suitable product found"


@freeze_time("2020-01-01T08:00:00Z")
def test_send_berth_invoices_missing_email(notification_template_orders_approved):
    lease = BerthLeaseFactory(
        renew_automatically=True,
        boat=None,
        status=LeaseStatus.PAID,
        start_date=today() - relativedelta(years=1),
        end_date=today() + relativedelta(years=-1, months=5),
    )
    customer = lease.customer
    price_group = BerthPriceGroup.objects.get_or_create_for_width(
        lease.berth.berth_type.width
    )
    BerthProductFactory(price_group=price_group, harbor=lease.berth.pier.harbor)

    user = UserFactory()

    r = RequestFactory().request(
        HTTP_API_TOKENS=f'{{"{PROFILE_TOKEN_SERVICE}": "token"}}'
    )
    data = {
        "id": to_global_id(ProfileNode, customer.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "primary_email": None,
    }

    assert Order.objects.count() == 0

    with mock.patch(
        "customers.services.profile.requests.post",
        side_effect=mocked_response_profile(count=0, data=data),
    ):
        result = send_berth_invoices(r)

    successful_orders: List[UUID] = result.get("successful_orders")
    failed_orders: List[Dict[UUID, str]] = result.get("failed_orders")
    failed_leases: List[Dict[UUID, str]] = result.get("failed_leases")

    assert len(successful_orders) == 0
    assert len(failed_orders) == 1
    assert len(failed_leases) == 0
    assert Order.objects.count() == 1

    order = Order.objects.first()

    assert order.status == OrderStatus.ERROR
    assert order.id in failed_orders[0].keys()
    assert failed_orders[0].get(order.id) == "Missing customer email"

    assert len(mail.outbox) == 0

    leases = BerthLease.objects.exclude(id=lease.id)
    assert leases.count() == 1
    lease: BerthLease = leases.first()
    assert lease.status == LeaseStatus.ERROR
    assert lease.start_date.isoformat() == "2020-06-10"
    assert lease.end_date.isoformat() == "2020-09-14"


@freeze_time("2020-01-01T08:00:00Z")
def test_send_berth_invoices_invalid_example_email(
    notification_template_orders_approved,
):
    lease = BerthLeaseFactory(
        renew_automatically=True,
        boat=None,
        status=LeaseStatus.PAID,
        start_date=today() - relativedelta(years=1),
        end_date=today() + relativedelta(years=-1, months=5),
    )
    customer = lease.customer
    price_group = BerthPriceGroup.objects.get_or_create_for_width(
        lease.berth.berth_type.width
    )
    BerthProductFactory(price_group=price_group, harbor=lease.berth.pier.harbor)

    user = UserFactory()

    r = RequestFactory().request(
        HTTP_API_TOKENS=f'{{"{PROFILE_TOKEN_SERVICE}": "token"}}'
    )
    data = {
        "id": to_global_id(ProfileNode, customer.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "primary_email": {"email": "something@example.com"},
    }

    assert Order.objects.count() == 0

    with mock.patch(
        "customers.services.profile.requests.post",
        side_effect=mocked_response_profile(count=0, data=data),
    ):
        result = send_berth_invoices(r)

    successful_orders: List[UUID] = result.get("successful_orders")
    failed_orders: List[Dict[UUID, str]] = result.get("failed_orders")
    failed_leases: List[Dict[UUID, str]] = result.get("failed_leases")

    assert len(successful_orders) == 0
    assert len(failed_orders) == 1
    assert len(failed_leases) == 0
    assert Order.objects.count() == 1

    order = Order.objects.first()

    assert order.status == OrderStatus.ERROR
    assert order.id in failed_orders[0].keys()
    assert failed_orders[0].get(order.id) == "Missing customer email"

    assert len(mail.outbox) == 0

    leases = BerthLease.objects.exclude(id=lease.id)
    assert leases.count() == 1
    lease: BerthLease = leases.first()
    assert lease.status == LeaseStatus.ERROR
    assert lease.start_date.isoformat() == "2020-06-10"
    assert lease.end_date.isoformat() == "2020-09-14"


@freeze_time("2020-01-01T08:00:00Z")
def test_send_berth_invoices_send_error(notification_template_orders_approved):
    lease = BerthLeaseFactory(
        renew_automatically=True,
        boat=None,
        status=LeaseStatus.PAID,
        start_date=today() - relativedelta(years=1),
        end_date=today() + relativedelta(years=-1, months=5),
    )
    customer = lease.customer
    price_group = BerthPriceGroup.objects.get_or_create_for_width(
        lease.berth.berth_type.width
    )
    BerthProductFactory(price_group=price_group, harbor=lease.berth.pier.harbor)

    user = UserFactory()

    r = RequestFactory().request(
        HTTP_API_TOKENS=f'{{"{PROFILE_TOKEN_SERVICE}": "token"}}'
    )
    data = {
        "id": to_global_id(ProfileNode, customer.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "primary_email": {"email": user.email},
    }

    assert Order.objects.count() == 0

    with mock.patch(
        "customers.services.profile.requests.post",
        side_effect=mocked_response_profile(count=0, data=data),
    ):
        with mock.patch(
            "payments.utils.send_notification",
            side_effect=AnymailError("Anymail error"),
        ):
            result = send_berth_invoices(r)

    successful_orders: List[UUID] = result.get("successful_orders")
    failed_orders: List[Dict[UUID, str]] = result.get("failed_orders")
    failed_leases: List[Dict[UUID, str]] = result.get("failed_leases")

    assert len(successful_orders) == 0
    assert len(failed_orders) == 1
    assert len(failed_leases) == 0
    assert Order.objects.count() == 1

    order = Order.objects.first()

    assert order.id in failed_orders[0].keys()
    assert failed_orders[0].get(order.id) == "Anymail error"

    assert len(mail.outbox) == 0

    leases = BerthLease.objects.exclude(id=lease.id)
    assert leases.count() == 1
    lease: BerthLease = leases.first()
    assert lease.status == LeaseStatus.ERROR
    assert lease.start_date.isoformat() == "2020-06-10"
    assert lease.end_date.isoformat() == "2020-09-14"

    assert order.status == OrderStatus.ERROR
    assert (
        order.log_entries.get(to_status=OrderStatus.ERROR).comment
        == "Lease renewing failed: Anymail error"
    )


@freeze_time("2020-01-01T08:00:00Z")
def test_send_berth_invoices_only_not_renewed(notification_template_orders_approved):
    # This lease should be ignored since it already has a lease for the upcoming season
    renewed_lease = BerthLeaseFactory(
        renew_automatically=True,
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_season_start_date(today() - relativedelta(years=1)),
        end_date=calculate_season_end_date(today() - relativedelta(years=1)),
    )
    # Renewed lease for the previous one
    BerthLeaseFactory(
        customer=renewed_lease.customer,
        berth=renewed_lease.berth,
        renew_automatically=True,
        boat=None,
        status=LeaseStatus.DRAFTED,
        start_date=calculate_season_start_date(today()),
        end_date=calculate_season_end_date(today()),
    )
    # This lease should be renewed
    valid_lease = BerthLeaseFactory(
        renew_automatically=True,
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_season_start_date(today() - relativedelta(years=1)),
        end_date=calculate_season_end_date(today() - relativedelta(years=1)),
    )

    customer = valid_lease.customer
    price_group = BerthPriceGroup.objects.get_or_create_for_width(
        valid_lease.berth.berth_type.width
    )
    BerthProductFactory(price_group=price_group, harbor=None)

    user = UserFactory()

    r = RequestFactory().request(
        HTTP_API_TOKENS=f'{{"{PROFILE_TOKEN_SERVICE}": "token"}}'
    )
    data = {
        "id": to_global_id(ProfileNode, customer.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "primary_email": {"email": user.email},
    }

    assert Order.objects.count() == 0

    with mock.patch(
        "customers.services.profile.requests.post",
        side_effect=mocked_response_profile(count=0, data=data),
    ):
        result = send_berth_invoices(r)

    successful_orders: List[UUID] = result.get("successful_orders")
    failed_orders: List[Dict[UUID, str]] = result.get("failed_orders")
    failed_leases: List[Dict[UUID, str]] = result.get("failed_leases")

    assert len(successful_orders) == 1
    assert len(failed_orders) == 0
    assert len(failed_leases) == 0
    assert Order.objects.count() == 1

    assert Order.objects.first().id == successful_orders[0]

    # The already renewed lease and the old one, plus the valid and it's renewed lease
    assert BerthLease.objects.count() == 4
    lease: BerthLease = BerthLease.objects.filter(
        customer=valid_lease.customer
    ).exclude(id=valid_lease.id).first()

    assert lease.status == LeaseStatus.OFFERED
    assert lease.start_date.isoformat() == "2020-06-10"
    assert lease.end_date.isoformat() == "2020-09-14"

    orders = Order.objects.all()
    assert orders.count() == 1
    order: Order = orders.first()
    assert successful_orders[0] == order.id
    assert order.lease == lease
    assert order.customer.id == customer.id
    assert order.status == OrderStatus.WAITING
