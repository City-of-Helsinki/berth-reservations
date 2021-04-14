import logging

import requests
from django.conf import settings
from django.core.management import BaseCommand
from django.db.models import Q

from customers.enums import OrganizationType
from customers.services import ProfileService
from customers.services.sms_notification_service import SMSNotificationService
from leases.enums import LeaseStatus
from leases.models import BerthLease
from payments.enums import OrderStatus
from payments.models import Order
from payments.providers import BamboraPayformProvider
from resources.enums import BerthMooringType
from resources.models import BerthType

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.setLevel(logging.DEBUG)
# create console handler and set level to debug
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)


class Command(BaseCommand):
    help = ""

    def add_arguments(self, parser):
        parser.add_argument(
            "--profile-token",
            nargs="?",
            type=str,
            help="[Required] The API token for Profile",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Only show a list of the invoices that can be sent "
            "and how many customer are missing phones in our system",
        )

    def handle(self, *args, profile_token=None, dry_run=False, **options):
        no_customer_phone = []
        sent = []
        failed = []

        # Exceptions are
        # - Jollapaikat
        # - Traileripaikat
        # - Non-billable customer group (Ei laskutettavat)
        # - Customers who are manually set to error (you know)
        # - Vasikkasaaren venesatama (all customers)

        # Exclude jollas and trailer places
        berth_types = BerthType.objects.exclude(
            mooring_type__in=(
                BerthMooringType.TRAWLER_PLACE,
                BerthMooringType.DINGHY_PLACE,
            )
        )

        # Get the ids of the leases, to later get the orders
        leases = (
            # Exclude the Vasikkasaari harbor
            BerthLease.objects.exclude(
                berth__pier__harbor_id="4e982440-d032-4d9e-a827-e1c89e86da51"
            )
            .filter(
                start_date__year=2021,
                status=LeaseStatus.OFFERED,
                berth__berth_type__in=berth_types,
            )
            .values("id")
        )
        orders = Order.objects.filter(
            Q(
                # Valid leases
                Q(_lease_object_id__in=leases)
                # Invoices that haven't been paid
                & Q(status=OrderStatus.OFFERED)
                & Q(
                    # Either "normal" customers
                    Q(customer__organization__isnull=True)
                    # Or "billable" organization customers
                    | Q(
                        customer__organization__organization_type__in=(
                            OrganizationType.COMPANY,
                            OrganizationType.OTHER,
                        )
                    )
                )
                # Only for production, since no invoices will have phone, it will work
                # as a flag to check which ones to send
                # customer_phone__isnull=True,
            )
        )

        profile_service = ProfileService(profile_token=profile_token)
        sms_service = SMSNotificationService()
        payment_provider = BamboraPayformProvider(
            ui_return_url=settings.VENE_UI_RETURN_URL
        )

        MESSAGE = (
            "Hyvä asiakas. Tässä maksulinkki venepaikan maksamiseen purjehduskaudelle 2021. "
            "Maksathan laskun 7.2.2021 mennessä.\n\n"
            "Kära kund. Här är en länk för att betala för kaj eller avsluta den för seglingsäsongen 2021. "
            "Vänligen betala fakturan senast den 7 februari 2021.\n\n"
            "{url}"
        )

        if dry_run:
            invoices = orders.count()
            without_phone = orders.filter(
                Q(Q(customer_phone__isnull=True) | Q(customer_phone=""))
            ).count()

            self.stdout.write(f"Invoices to be sent: {invoices}")
            self.stdout.write(f"Customers without phone: {without_phone}")

            return

        for order in orders:
            # If the order doesn't have a customer phone number, fetch it from Profiili
            if not order.customer_phone:
                logger.debug(f"Fetching profile for: {order.customer.id}")
                try:
                    customer = profile_service.get_profile(order.customer.id)
                except Exception:
                    no_customer_phone.append(f"{order.id};{order.customer.id}\n")
                    continue

                # If the customer doesn't have a phone in Profiili, add it to the failures
                # so the admins can handle it manually
                if not customer.phone:
                    no_customer_phone.append(f"{order.id};{order.customer.id}\n")
                    continue

                # Save the phone to the order, in case it is required later
                order.customer_phone = customer.phone
                order.save()
            else:
                logger.debug(f"Phone found for: {order.customer.id}")

            message = MESSAGE.format(
                url=payment_provider.get_payment_email_url(order, "fi")
            )

            try:
                result = sms_service.send_plain_text(order.customer_phone, message)
                if result.status_code == 200:
                    # Keep track of the successful orders, in case there needs to be any follow-up
                    sent.append(f"{order.id}\n")
                else:
                    failed.append(f"{order.id};Failed with status {result.status_code}")
            except requests.exceptions.RequestException as e:
                failed.append(f"{order.id};{e}")
                logger.exception(e)

        self.stdout.write(self.style.SUCCESS(f"Sent {len(sent)} messages"))
        with open("sent_sms.txt", "w+") as file:
            file.writelines(sent)

        self.stdout.write(self.style.ERROR(f"Failed to send: {len(failed)}"))
        logger.error(failed)
        with open("failed.txt", "w+") as file:
            file.writelines(failed)

        self.stdout.write(self.style.ERROR(f"No phone found: {len(no_customer_phone)}"))
        logger.error(no_customer_phone)
        with open("no_customer_phone.txt", "w+") as file:
            file.writelines(no_customer_phone)
