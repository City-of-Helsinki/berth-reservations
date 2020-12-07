import logging
from datetime import date
from typing import Dict, List, Union
from uuid import UUID

from anymail.exceptions import AnymailError
from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from django.core.exceptions import ValidationError
from django.db import DataError, IntegrityError, transaction
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from berth_reservations.exceptions import VenepaikkaGraphQLError
from customers.services import HelsinkiProfileUser, ProfileService
from leases.enums import LeaseStatus
from leases.exceptions import AutomaticInvoicingError
from leases.models import BerthLease, WinterStorageLease
from leases.utils import calculate_season_end_date, calculate_season_start_date
from payments.enums import OrderStatus
from payments.models import BerthPriceGroup, BerthProduct, Order, WinterStorageProduct
from payments.utils import approve_order

logger = logging.getLogger(__name__)


class BaseInvoicingService:
    MAXIMUM_FAILURES = 50

    successful_orders: List[UUID]
    failed_leases: List[Dict[UUID, str]]
    failed_orders: List[Dict[UUID, str]]
    failure_count: int

    season_start: date
    season_end: date
    due_date: date

    request: HttpRequest
    profile_token: str

    def __init__(self, request: HttpRequest, profile_token: str, due_date: date = None):
        # Default the due date to 14 days from the date when the task is executed
        self.request = request
        self.profile_token = profile_token
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
        self.failure_count += 1

    def fail_order(self, order: Order, message: str,) -> None:
        """Set an order to ERROR status and append it to the failed_order list"""
        order.comment = f"{today().date()}: {message}"
        order.save(update_fields=["comment"])
        order.set_status(OrderStatus.ERROR, f"Lease renewing failed: {message}")
        self.failed_orders.append({order.id: message})
        self.failure_count += 1

    def send_email(self, order, helsinki_profile_user: HelsinkiProfileUser):
        email = helsinki_profile_user.email if helsinki_profile_user else None

        # If the profile doesn't have an associated email
        # or if it has an example.com address, set it as failed
        if email and "example.com" not in email:
            try:
                approve_order(
                    order, email, self.due_date, helsinki_profile_user, self.request
                )
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

        self.failure_count = 0

        leases = self.get_valid_leases(self.season_start)

        # Fetch all the profiles from the Profile service
        profiles = ProfileService(self.profile_token).get_all_profiles()

        for lease in leases:
            order = None
            if self.failure_count >= self.MAXIMUM_FAILURES:
                raise AutomaticInvoicingError(
                    _(
                        f"Limit of failures reached: {self.failure_count} elements failed"
                    )
                )

            if lease.customer.id not in profiles:
                self.fail_lease(
                    lease, _("The application is not connected to a customer")
                )
                continue

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

                        helsinki_profile_user = profiles.get(customer.id)
                        self.send_email(order, helsinki_profile_user)
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
        return BerthLease.objects.get_renewable_leases(season_start=season_start)
