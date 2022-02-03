import hashlib
from datetime import date
from typing import Tuple

from dateutil.relativedelta import relativedelta

from leases.utils import calculate_season_end_date, calculate_season_start_date
from utils.relay import from_global_id


def calculate_lease_start_and_end_dates(start_date: date) -> Tuple[date, date]:
    """
    When importing customers from the old Timmi system, we try to create leases based on the order data we have.
    For that, we use the created_at timestamp of the order. Assuming that the order was generated for the
    upcoming season, we calculate the start and end dates for the lease.
    """
    end_date = calculate_season_end_date(start_date)

    # If the start date is after the calculated end date for the associated season (year),
    # the lease would belong to the next year's season
    if start_date > end_date:
        start_date = calculate_season_start_date(start_date) + relativedelta(years=1)
        end_date = calculate_season_end_date(start_date)
    # If the order was created before the start date's year's season start, the start date will
    # be the that year's season
    elif start_date < calculate_season_start_date(start_date):
        start_date = calculate_season_start_date(start_date)
    # Otherwise, if the start date is during the season dates, it should be the same

    return start_date, end_date


def get_customer_hash(profile) -> str:
    return hashlib.sha256(str(profile.id).encode()).hexdigest()


def from_global_ids(global_ids: [str], node_type: object) -> [str]:
    return [from_global_id(gid, node_type) for gid in global_ids]
