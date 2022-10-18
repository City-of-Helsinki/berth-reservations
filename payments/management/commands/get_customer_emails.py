from calendar import month_name
from datetime import date
from itertools import chain
from typing import Optional, Tuple, Union

from django.core.management import BaseCommand
from django.db.models import QuerySet

from payments.models import Order

# Invoices for the next season's berth orders
# (i.e. "seuraavan kauden venepaikkojen laskut") start to be sent during December
# (e.g. 7th of December), relaxed lower bound is 1st of December.
BERTH_ORDERS_START_DAY = 1
BERTH_ORDERS_START_MONTH = 12
BERTH_ORDERS_END_DAY = 14  # Inclusive range
BERTH_ORDERS_END_MONTH = 9  # Inclusive range
BERTH_ORDERS_END_NEXT_YEAR = True

# Invoices for the next season's winter storage orders
# (i.e. "seuraavan kauden talvisäilytyspaikkojen laskut") start to be sent during August
# (e.g. 15th of August), relaxed lower bound is 1st of August.
WINTER_STORAGE_ORDERS_START_DAY = 1
WINTER_STORAGE_ORDERS_START_MONTH = 8
WINTER_STORAGE_ORDERS_END_DAY = 9  # Inclusive range
WINTER_STORAGE_ORDERS_END_MONTH = 6  # Inclusive range
WINTER_STORAGE_ORDERS_END_NEXT_YEAR = True


def is_valid_email(email: Optional[str]) -> bool:
    return email is not None and "@" in email


def get_order_email(order: Order) -> Optional[str]:
    email = order.customer_email
    if not email:
        if order.lease and order.lease.application:
            email = order.lease.application.email
    return email.strip() if email and email.strip() else None


def get_output_filename(today: Union[str, date]) -> str:
    return f"customer_emails_{today}.txt"


def get_orders_date_range(
    today: date,
    start_day: int,
    start_month: int,
    end_day: int,  # Inclusive range
    end_month: int,  # Inclusive range
    end_next_year: bool,
) -> Tuple[date, date]:
    end_year_start_year_difference: int = 1 if end_next_year else 0
    start_year = (
        today.year - end_year_start_year_difference
        if (today.month, today.day) < (start_month, start_day)
        else today.year
    )
    return (
        date(start_year, start_month, start_day),
        date(start_year + end_year_start_year_difference, end_month, end_day),
    )


def get_berth_orders_date_range(today: date) -> Tuple[date, date]:
    return get_orders_date_range(
        today=today,
        start_day=BERTH_ORDERS_START_DAY,
        start_month=BERTH_ORDERS_START_MONTH,
        end_day=BERTH_ORDERS_END_DAY,
        end_month=BERTH_ORDERS_END_MONTH,
        end_next_year=BERTH_ORDERS_END_NEXT_YEAR,
    )


def get_winter_storage_orders_date_range(today: date) -> Tuple[date, date]:
    return get_orders_date_range(
        today=today,
        start_day=WINTER_STORAGE_ORDERS_START_DAY,
        start_month=WINTER_STORAGE_ORDERS_START_MONTH,
        end_day=WINTER_STORAGE_ORDERS_END_DAY,
        end_month=WINTER_STORAGE_ORDERS_END_MONTH,
        end_next_year=WINTER_STORAGE_ORDERS_END_NEXT_YEAR,
    )


def get_help_text():
    return f"""
        Get customer emails from berth and winter storage orders active on given date
        <TODAY> and save them to {get_output_filename("<TODAY>")}.
        TODAY is determined by the parameters YEAR, MONTH and DAY.

        Emails are included from berth orders (venepaikkatilaukset) created between
        {month_name[BERTH_ORDERS_START_MONTH]} {BERTH_ORDERS_START_DAY} –
        {month_name[BERTH_ORDERS_END_MONTH]} {BERTH_ORDERS_END_DAY}
        {" next year" if BERTH_ORDERS_END_NEXT_YEAR else " the same year"}
        for such a time period which contains <TODAY>.

        Emails are included from winter storage orders (talvisäilytystilaukset) created between
        {month_name[WINTER_STORAGE_ORDERS_START_MONTH]} {WINTER_STORAGE_ORDERS_START_DAY} –
        {month_name[WINTER_STORAGE_ORDERS_END_MONTH]} {WINTER_STORAGE_ORDERS_END_DAY}
        {" next year" if WINTER_STORAGE_ORDERS_END_NEXT_YEAR else " the same year"}
        for such a time period which contains <TODAY>.
    """.strip()


class Command(BaseCommand):
    help = get_help_text()

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            "-y",
            metavar="Y",
            dest="year",
            type=int,
            default=date.today().year,
            help="Year for which to gather customer emails. Default: Current year",
        )
        parser.add_argument(
            "--month",
            "-m",
            metavar="M",
            dest="month",
            type=int,
            default=date.today().month,
            help="Month for which to gather customer emails. Default: Current month",
        )
        parser.add_argument(
            "--day",
            "-d",
            metavar="D",
            dest="day",
            type=int,
            default=date.today().day,
            help="Day for which to gather customer emails. Default: Current day",
        )
        parser.add_argument(
            "--encoding",
            "-e",
            metavar="E",
            dest="encoding",
            type=str,
            default="utf-8",
            help="Output encoding. Default: %(default)s",
        )
        parser.add_argument(
            "--exclude-berth-orders",
            dest="exclude_berth_orders",
            action="store_true",
            default=False,
            help="Exclude berth orders (venepaikkatilaukset). Default: %(default)s",
        )
        parser.add_argument(
            "--exclude-winter-storage-orders",
            dest="exclude_winter_storage_orders",
            action="store_true",
            default=False,
            help="Exclude winter storage orders (talvisäilytystilaukset). Default: %(default)s",
        )
        parser.add_argument(
            "--use-posix-line-separator",
            dest="use_posix_line_separator",
            action="store_true",
            default=False,
            help=(
                "Use POSIX line separator \\n in output? "
                "If not, use Windows line separator \\r\\n. Default: %(default)s"
            ),
        )

    def handle(
        self,
        *args,
        year: int,
        month: int,
        day: int,
        encoding: str,
        exclude_berth_orders: bool,
        exclude_winter_storage_orders: bool,
        use_posix_line_separator: bool,
        **options,
    ):
        today: date = date(year=year, month=month, day=day)
        berth_orders: QuerySet[Order] = Order.objects.none()
        winter_storage_orders: QuerySet[Order] = Order.objects.none()

        if exclude_berth_orders:
            self.stdout.write(self.style.WARNING("Excluding berth orders"))
        else:
            min_date, max_date = get_berth_orders_date_range(today)
            berth_orders = Order.objects.berth_orders().filter(
                created_at__date__gte=min_date, created_at__date__lte=max_date
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Found {len(berth_orders)} berth orders "
                    f"created between {min_date} – {max_date}"
                )
            )

        if exclude_winter_storage_orders:
            self.stdout.write(self.style.WARNING("Excluding winter storage orders"))
        else:
            min_date, max_date = get_winter_storage_orders_date_range(today)
            winter_storage_orders = Order.objects.winter_storage_orders().filter(
                created_at__date__gte=min_date, created_at__date__lte=max_date
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Found {len(winter_storage_orders)} winter storage orders "
                    f"created between {min_date} – {max_date}"
                )
            )

        emails = sorted(
            set(
                filter(
                    is_valid_email,
                    (
                        get_order_email(order)
                        for order in chain(berth_orders, winter_storage_orders)
                    ),
                )
            )
        )

        if emails:
            output_filename = get_output_filename(today)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Writing {len(emails)} unique emails to {output_filename}"
                )
            )
            with open(
                output_filename,
                mode="w",
                encoding=encoding,
                newline="\n" if use_posix_line_separator else "\r\n",
            ) as file:
                # \n are converted to open call's newline
                file.write("\n".join(emails) + "\n")
        else:
            self.stdout.write(self.style.WARNING(f"No emails found for date {today}"))
