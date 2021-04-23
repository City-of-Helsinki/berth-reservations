from datetime import date

from django.db.models import QuerySet

from payments.enums import OrderStatus
from payments.models import BerthProduct, Order

from ...models import BerthLease
from ...utils import calculate_season_end_date, calculate_season_start_date
from .base import BaseInvoicingService


class BerthInvoicingService(BaseInvoicingService):
    def __init__(self, *args, **kwargs):
        super(BerthInvoicingService, self).__init__(*args, **kwargs)
        self.season_start = calculate_season_start_date()
        self.season_end = calculate_season_end_date()

    @staticmethod
    def get_product(lease: BerthLease) -> BerthProduct:
        # The berth product is determined by the width of the berth of the lease
        return BerthProduct.objects.get_in_range(width=lease.berth.berth_type.width)

    @staticmethod
    def get_valid_leases(season_start: date) -> QuerySet:
        return BerthLease.objects.get_renewable_leases(season_start=season_start)

    @staticmethod
    def get_failed_orders(season_start: date) -> QuerySet:
        leases = BerthLease.objects.filter(
            start_date__year=season_start.year
        ).values_list("id")

        return Order.objects.filter(
            _lease_object_id__in=leases, status=OrderStatus.ERROR
        )
