import logging
from datetime import date
from typing import Dict, List, Union
from uuid import UUID

import pytz
from anymail.exceptions import AnymailError
from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import DataError, IntegrityError, transaction
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django_ilmoitin.utils import send_notification

from berth_reservations.exceptions import VenepaikkaGraphQLError
from contracts.models import VismaBerthContract, VismaWinterStorageContract
from customers.services import HelsinkiProfileUser, ProfileService
from leases.enums import LeaseStatus
from leases.exceptions import AutomaticInvoicingError
from leases.models import BerthLease, WinterStorageLease
from payments.enums import OrderStatus
from payments.models import BerthProduct, Order, WinterStorageProduct
from payments.utils import approve_order, resend_order, update_order_from_profile
from utils.email import is_valid_email

from ...notifications import NotificationType as LeaseNotificationType

logger = logging.getLogger(__name__)


def get_ts() -> str:
    return (
        now()
        .astimezone(pytz.timezone(settings.TIME_ZONE))
        .strftime("%d-%m-%Y %H:%M:%S")
    )


class BaseInvoicingService:
    MAXIMUM_FAILURES = 100

    ADMIN_EMAIL_NOTIFICATION_GROUP_NAME = "Berth services"

    successful_orders: List[UUID]
    processed_leases: List[UUID]
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

        self.successful_orders = []
        self.failed_orders = []
        self.failed_leases = []
        self.processed_leases = []

        self.failure_count = 0

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
    def get_failed_orders(season_start: date) -> QuerySet:
        raise NotImplementedError

    @staticmethod
    def create_new_lease(
        lease: Union[BerthLease, WinterStorageLease], start_date: date, end_date: date
    ) -> Union[BerthLease, WinterStorageLease]:
        """Create a new lease instance"""

        # Make copy of attached contract, if one exists and if the customer is billable.
        contract = None
        if (
            hasattr(lease, "contract")
            and lease.contract is not None
            and not lease.customer.is_non_billable_customer()
        ):
            contract = lease.contract

        # Blank the PK to signal that a new instance has to be created
        lease.pk = None

        # Manually need to set creating because of the checks performed on clean
        lease._state.adding = True

        # Update the dates for the lease for the next season
        lease.start_date = start_date
        lease.end_date = end_date

        # Set correct status
        lease.status = LeaseStatus.DRAFTED

        # If the previous lease has an application attached,
        # it will fail since it is a OneToOne field
        lease.application = None

        lease.save()

        if contract:
            if isinstance(lease, BerthLease):
                VismaBerthContract.objects.create(
                    lease=lease,
                    document_id=contract.document_id,
                    invitation_id=contract.invitation_id,
                    passphrase=contract.passphrase,
                    status=contract.status,
                )
            elif isinstance(lease, WinterStorageLease):
                VismaWinterStorageContract.objects.create(
                    lease=lease,
                    document_id=contract.document_id,
                    invitation_id=contract.invitation_id,
                    passphrase=contract.passphrase,
                    status=contract.status,
                )

        lease.refresh_from_db()

        return lease

    def fail_lease(
        self,
        lease: Union[BerthLease, WinterStorageLease],
        message: str,
        dont_count: bool = False,
    ) -> None:
        """Set a lease to ERROR status and append it to the failed_lease list"""
        lease.status = LeaseStatus.ERROR
        comment = f"{get_ts()}: {message}"

        if len(lease.comment) > 0:
            lease.comment += f"\n{comment}"
        else:
            lease.comment = comment

        lease.save(update_fields=["status", "comment"])
        self.failed_leases.append({lease.id: message})
        self.failure_count += 1 if not dont_count else 0
        logger.debug(f"Lease failed [{lease.id}]: {message}")

    def fail_order(self, order: Order, message: str, dont_count: bool = False) -> None:
        """Set an order to ERROR status and append it to the failed_order list"""
        order.set_status(OrderStatus.ERROR, f"Lease renewing failed: {message}")
        order.comment = f"{get_ts()}: {message}"
        order.due_date = None
        order.save(update_fields=["comment", "due_date"])
        self.failed_orders.append({order.id: message})
        self.failure_count += 1 if not dont_count else 0
        logger.debug(f"Lease order [{order.id}]: {message}")

    def send_email(self, order, helsinki_profile_user: HelsinkiProfileUser):
        email = helsinki_profile_user.email if helsinki_profile_user else None

        # If the profile doesn't have an associated email
        # or if it has an example.com address, set it as failed
        if is_valid_email(email):
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
            self.fail_lease(order.lease, _("Missing customer email"), dont_count=True)
            self.fail_order(order, _("Missing customer email"), dont_count=True)

    @property
    def number_of_failed_orders(self):
        # for every lease, an order needs to be created. If lease processing does not
        # end with a successful order, then it's a failure.
        return len(self.processed_leases) - len(self.successful_orders)

    def email_admins(self, exited_with_errors: bool = False):
        logger.debug("Emailing admins")
        context = {
            "subject": LeaseNotificationType.AUTOMATIC_INVOICING_EMAIL_ADMINS.label,
            "exited_with_errors": exited_with_errors,
            "successful_orders": len(self.successful_orders),
            "failed_orders": self.number_of_failed_orders,
        }
        admins = (
            get_user_model()
            .objects.filter(
                groups=Group.objects.get(name=self.ADMIN_EMAIL_NOTIFICATION_GROUP_NAME)
            )
            .exclude(email="")
            .exclude(email__icontains="@example.com")
        )
        for admin in admins:
            send_notification(
                admin.email,
                LeaseNotificationType.AUTOMATIC_INVOICING_EMAIL_ADMINS,
                context,
            )

    def send_invoices(self) -> None:  # noqa: C901
        logger.info("Starting batch invoice sending")

        leases = self.get_valid_leases(self.season_start)
        logger.info(f"Leases to be renewed: {len(leases)}")

        failed_order_customers = list(
            self.get_failed_orders(self.season_start)
            .distinct("customer_id")
            .values_list("customer_id", flat=True)
            .order_by()
        )
        lease_customers = list(
            leases.distinct("customer_id")
            .values_list("customer_id", flat=True)
            .order_by()
        )

        # Fetch all the profiles from the Profile service
        profile_ids = list(set(failed_order_customers + lease_customers))
        logger.debug("Fetching profiles")
        profiles = ProfileService(self.profile_token).get_all_profiles(
            profile_ids=profile_ids
        )

        logger.info(f"Profiles fetched: {len(profiles)}")

        self.resend_failed_invoices(profiles)

        exited_with_errors = False
        try:
            for lease in leases:
                order = None
                if self.failure_count >= self.MAXIMUM_FAILURES:
                    error_message = _(
                        f"Limit of failures reached: {self.failure_count} elements failed"
                    )
                    logger.error(error_message)
                    raise AutomaticInvoicingError(error_message)

                self.processed_leases.append(lease.id)

                if lease.customer.id not in profiles:
                    self.fail_lease(
                        lease, _("The application is not connected to a customer")
                    )
                    continue

                try:
                    with transaction.atomic():
                        try:
                            new_lease = self.create_new_lease(
                                lease, self.season_start, self.season_end
                            )
                        except (ValueError, IntegrityError) as e:
                            logger.exception(e)
                            self.fail_lease(lease, str(e))
                            continue
                        customer = new_lease.customer

                        try:
                            order = Order.objects.create(
                                lease=new_lease, customer=customer
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
        except AutomaticInvoicingError:
            exited_with_errors = True
        finally:
            self.email_admins(exited_with_errors)
            logger.info("Finished batch invoicing")
            logger.info(f"Successful orders: {len(self.successful_orders)}")
            logger.info(f"Failed orders: {self.number_of_failed_orders}")
            logger.info(f"{exited_with_errors=}")

    def resend_failed_invoices(self, profiles: dict) -> None:
        logger.info("Resending failed invoices")

        orders = self.get_failed_orders(self.season_start)
        logger.info(f"Failed leases to be resent: {orders.count()}")

        for order in orders:
            order.due_date = self.due_date
            order.set_status(
                OrderStatus.OFFERED,
                comment=f"{get_ts()}: {_('Cleanup the invoice to attempt resending')}\n",
            )

            try:
                update_order_from_profile(order, profiles[order.customer.id])
                resend_order(order, self.due_date, self.request)
                self.successful_orders.append(order.id)
            except (
                AnymailError,
                OSError,
                Order.DoesNotExist,
                ValidationError,
                VenepaikkaGraphQLError,
            ) as e:
                self.fail_order(order, f'{_("Failed resending invoice")} ({e})')
            except KeyError as missing_key:
                self.fail_order(
                    order,
                    f'{_("Failed resending invoice")} (Missing profile: {missing_key})',
                )
