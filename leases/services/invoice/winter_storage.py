from datetime import date

from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from django.db.models import QuerySet

from payments.enums import OrderStatus
from payments.models import Order, WinterStorageProduct

from ...models import WinterStorageLease
from ...utils import (
    calculate_winter_season_end_date,
    calculate_winter_season_start_date,
)
from .base import BaseInvoicingService


class WinterStorageInvoicingService(BaseInvoicingService):
    def __init__(self, *args, **kwargs):
        super(WinterStorageInvoicingService, self).__init__(*args, **kwargs)

        current_date = today().date()
        if current_date.year == calculate_winter_season_start_date().year:
            self.season_start = calculate_winter_season_start_date() + relativedelta(
                year=current_date.year + 1
            )
            self.season_end = calculate_winter_season_end_date() + relativedelta(
                year=current_date.year + 2
            )
        else:
            self.season_start = calculate_winter_season_start_date() + relativedelta(
                year=current_date.year
            )
            self.season_end = calculate_winter_season_end_date() + relativedelta(
                year=current_date.year + 1
            )

    @staticmethod
    def get_product(lease: WinterStorageLease) -> WinterStorageProduct:
        area = (
            lease.section.area
            if lease.section
            else lease.place.winter_storage_section.area
        )
        return WinterStorageProduct.objects.get(winter_storage_area=area)

    @staticmethod
    def get_valid_leases(season_start: date) -> QuerySet:
        return WinterStorageLease.objects.get_renewable_marked_leases(
            season_start - relativedelta(years=1)
        )

    @staticmethod
    def get_failed_orders(season_start: date) -> QuerySet:
        leases = WinterStorageLease.objects.filter(
            start_date__year=season_start.year
        ).values_list("id")

        return Order.objects.filter(
            _lease_object_id__in=leases, status=OrderStatus.ERROR
        )
