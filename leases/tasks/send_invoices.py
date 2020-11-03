from datetime import date
from typing import Dict, List, Union
from uuid import UUID

from anymail.exceptions import AnymailError
from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Exists, OuterRef, QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from berth_reservations.exceptions import VenepaikkaGraphQLError
from customers.services import ProfileService
from customers.services.profile import HelsinkiProfileUser
from leases.enums import LeaseStatus
from leases.models import BerthLease, WinterStorageLease
from leases.utils import calculate_season_end_date, calculate_season_start_date
from payments.enums import OrderStatus
from payments.models import BerthPriceGroup, BerthProduct, Order, WinterStorageProduct
from payments.utils import approve_order

BERTH_LEASES = "berth_leases"
WINTER_LEASES = "winter_leases"


def fail_lease(
    lease: Union[BerthLease, WinterStorageLease],
    message: str,
    failed_leases: List[Dict[UUID, str]],
) -> None:
    """Set a lease to ERROR status and append it to the failed_lease list"""
    failed_leases.append({lease.id: message})
    lease.status = LeaseStatus.ERROR
    lease.save(update_fields=["status"])


def fail_order(
    order: Order, message: str, failed_orders: List[Dict[UUID, str]]
) -> None:
    """Set an order to ERROR status and append it to the failed_order list"""
    failed_orders.append({order.id: message})
    order.set_status(OrderStatus.ERROR, f"Lease renewing failed: {message}")


def get_product(
    lease: Union[BerthLease, WinterStorageLease]
) -> Union[BerthProduct, WinterStorageProduct]:
    """Get the product associated to the lease"""

    if isinstance(lease, BerthLease):
        return get_berth_product(lease)

    return get_winter_storage_product(lease)


def get_berth_product(lease: BerthLease) -> BerthProduct:
    # Many pre-imported leases don't have a boat associated, so we try to get the
    # width based on the berth_type.
    width = lease.boat.width if lease.boat else lease.berth.berth_type.width

    products_for_pricegroup = BerthProduct.objects.filter(
        price_group=BerthPriceGroup.objects.get_for_width(width),
    )

    # Get the product for the associated Harbor
    if harbor_product := products_for_pricegroup.filter(
        harbor=lease.berth.pier.harbor
    ).first():
        product = harbor_product

    # If there's no Harbor-specific product, try with the "default" product
    else:
        product = products_for_pricegroup.filter(harbor__isnull=True).first()

    return product


def get_winter_storage_product(lease: WinterStorageLease) -> WinterStorageProduct:
    raise NotImplementedError


def get_valid_leases(season_start: date, lease_type: str) -> QuerySet:
    if lease_type == BERTH_LEASES:
        return get_valid_berth_leases(season_start)
    return get_valid_winter_storage_leases(season_start)


def get_valid_winter_storage_leases(season_start: date) -> QuerySet:
    raise NotImplementedError


def get_valid_berth_leases(season_start: date) -> QuerySet:
    """
    Get the leases that were active last year
    If today is:
      (1) before season: leases from last year
      (2) during or after season: leases from this year
    """

    current_date = today().date()
    # If today is before the season starts but during the same year (1)
    if current_date < season_start and current_date.year == season_start.year:
        lease_year = current_date.year - 1
    else:  # (2)
        lease_year = current_date.year

    # Filter leases from the upcoming season
    future_leases = BerthLease.objects.filter(
        start_date__year__gt=lease_year,
        berth=OuterRef("berth"),
        customer=OuterRef("customer"),
    )

    # Exclude leases that have already been assigned to the same customer and berth on the future
    leases: QuerySet = BerthLease.objects.exclude(
        Exists(future_leases.values("pk"))
    ).filter(
        # Only allow leases that are auto-renewing and have been paid
        renew_automatically=True,
        status=LeaseStatus.PAID,
        start_date__year=lease_year,
        end_date__year=lease_year,
    )

    return leases


def create_new_lease(
    lease: Union[BerthLease, WinterStorageLease], start_date: date, end_date: date
) -> Union[BerthLease, WinterStorageLease]:
    """Create a new lease instance"""

    # Blank the PK to signal that a new instance has to be created
    lease.pk = None

    # Manually need to set creating because of the checks performed on clean
    lease._state.adding = True

    # Update the dates for the lease for the next season
    lease.start_date = start_date
    lease.end_date = end_date
    lease.save()

    return lease


def send_berth_invoices(request: HttpRequest, due_date: date = None) -> Dict[str, List]:
    return send_invoices(
        request,
        BERTH_LEASES,
        season_start=calculate_season_start_date(),
        season_end=calculate_season_end_date(),
        due_date=due_date,
    )


def send_winter_storage_invoices(
    request: HttpRequest, due_date: date = None
) -> Dict[str, List]:
    raise NotImplementedError


@transaction.atomic
def send_invoices(
    request: HttpRequest,
    lease_type: str,
    season_start: date,
    season_end: date,
    due_date: date = None,
) -> Dict[str, List]:  # noqa: C901
    successful_orders: List[UUID] = []
    failed_orders: List[Dict[UUID, str]] = []
    failed_leases: List[Dict[UUID, str]] = []

    # Default the due date to 14 days from the date when the task is executed
    if not due_date:
        due_date = today() + relativedelta(days=14)

    leases = get_valid_leases(season_start, lease_type)

    orders: List[Order] = []

    for lease in leases:
        lease = create_new_lease(lease, season_start, season_end)

        # Get the associated product
        product = get_product(lease)

        # If no product is found, the billing can't be done
        if not product:
            fail_lease(lease, _("No suitable product found"), failed_leases)
            continue

        try:
            order = Order.objects.create(
                customer=lease.customer, lease=lease, product=product
            )
            orders.append(order)
        except ValidationError as e:
            fail_lease(lease, str(e), failed_leases)

    # Fetch all the profiles from the Profile service
    profiles: Dict[UUID, HelsinkiProfileUser] = ProfileService(
        request
    ).get_all_profiles()

    # Go through all the created orders
    for order in orders:
        # If the profile doesn't have an associated email or if it has an example.com address, set it as failed
        email = profiles.get(order.customer.id).email
        if email and "example.com" not in email:
            try:
                approve_order(order, email, due_date, request)
                successful_orders.append(order.id)
            except (
                AnymailError,
                OSError,
                ValidationError,
                VenepaikkaGraphQLError,
            ) as e:
                fail_order(order, str(e), failed_orders)
        else:
            fail_order(order, _("Missing customer email"), failed_orders)

    return {
        "successful_orders": successful_orders,
        "failed_orders": failed_orders,
        "failed_leases": failed_leases,
    }
