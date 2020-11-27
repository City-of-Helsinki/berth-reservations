import logging
from datetime import date
from typing import Dict, List, Union
from uuid import UUID

from anymail.exceptions import AnymailError
from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from django.core.exceptions import ValidationError
from django.db import DataError, IntegrityError, transaction
from django.db.models import Exists, OuterRef, QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from berth_reservations.exceptions import VenepaikkaGraphQLError
from customers.services import ProfileService
from leases.enums import LeaseStatus
from leases.models import BerthLease, WinterStorageLease
from leases.utils import calculate_season_end_date, calculate_season_start_date
from payments.enums import OrderStatus
from payments.models import BerthPriceGroup, BerthProduct, Order, WinterStorageProduct
from payments.utils import approve_order

logger = logging.getLogger(__name__)


class BaseInvoicingService:
    successful_orders: List[UUID]
    failed_leases: List[Dict[UUID, str]]
    failed_orders: List[Dict[UUID, str]]

    season_start: date
    season_end: date
    due_date: date

    request: HttpRequest

    def __init__(self, request: HttpRequest, due_date: date = None):
        # Default the due date to 14 days from the date when the task is executed
        self.request = request
        self.due_date = due_date or (today() + relativedelta(days=14)).date()

    @staticmethod
    def get_product(
        lease: Union[BerthLease, WinterStorageLease]
    ) -> Union[BerthProduct, WinterStorageProduct]:
        """Get the product associated to the lease"""
        raise NotImplementedError

    @staticmethod
    def get_valid_leases(season_start: date) -> QuerySet:
        raise NotImplementedError

    @staticmethod
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

        # If the previous lease has an application attached,
        # it will fail since it is a OneToOne field
        lease.application = None

        lease.save(update_fields=["start_date", "end_date", "application"])

        return lease

    def fail_lease(
        self, lease: Union[BerthLease, WinterStorageLease], message: str
    ) -> None:
        """Set a lease to ERROR status and append it to the failed_lease list"""
        lease.status = LeaseStatus.ERROR
        comment = f"{today().date()}: {message}"

        if len(lease.comment) > 0:
            lease.comment += f"\n{comment}"
        else:
            lease.comment = comment

        lease.save(update_fields=["status", "comment"])
        self.failed_leases.append({lease.id: message})

    def fail_order(self, order: Order, message: str,) -> None:
        """Set an order to ERROR status and append it to the failed_order list"""
        order.comment = f"{today().date()}: {message}"
        order.save(update_fields=["comment"])
        order.set_status(OrderStatus.ERROR, f"Lease renewing failed: {message}")
        self.failed_orders.append({order.id: message})

    def send_email(self, order, email):
        # If the profile doesn't have an associated email
        # or if it has an example.com address, set it as failed
        if email and "example.com" not in email:
            try:
                approve_order(order, email, self.due_date, self.request)
                self.successful_orders.append(order.id)
            except (
                AnymailError,
                OSError,
                ValidationError,
                VenepaikkaGraphQLError,
            ) as e:
                logger.exception(e)
                self.fail_order(order, str(e))
        else:
            self.fail_order(order, _("Missing customer email"))

    def send_invoices(self) -> Dict[str, List]:  # noqa: C901
        self.successful_orders = []
        self.failed_orders = []
        self.failed_leases = []

        leases = self.get_valid_leases(self.season_start)

        # Fetch all the profiles from the Profile service
        profiles = ProfileService(self.request).get_all_profiles()

        for lease in leases:
            order = None
            try:
                with transaction.atomic():
                    new_lease = self.create_new_lease(
                        lease, self.season_start, self.season_end
                    )
                    customer = new_lease.customer

                    # Get the associated product
                    product = self.get_product(new_lease)

                    # If no product is found, the billing can't be done
                    if not product:
                        self.fail_lease(new_lease, _("No suitable product found"))
                        continue

                    try:
                        order = Order.objects.create(
                            customer=customer, lease=new_lease, product=product
                        )

                        self.send_email(
                            order, profiles.get(customer.id).email,
                        )
                    except ValidationError as e:
                        logger.exception(e)
                        self.fail_lease(new_lease, str(e))
            except (IntegrityError, DataError) as e:
                logger.exception(e)
                lease.refresh_from_db()
                self.fail_lease(lease, str(e))
                if order:
                    self.fail_order(order, str(e))
                pass
            # Catch any other problem that could come up to avoid breaking the task
            except Exception as e:
                logger.exception(e)

        return {
            "successful_orders": self.successful_orders,
            "failed_orders": self.failed_orders,
            "failed_leases": self.failed_leases,
        }


class BerthInvoicingService(BaseInvoicingService):
    def __init__(self, *args, **kwargs):
        super(BerthInvoicingService, self).__init__(*args, **kwargs)
        self.season_start = calculate_season_start_date()
        self.season_end = calculate_season_end_date()

    @staticmethod
    def get_product(lease: BerthLease) -> BerthProduct:
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

    @staticmethod
    def get_valid_leases(season_start: date) -> QuerySet:
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
