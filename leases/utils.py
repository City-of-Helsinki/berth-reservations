from datetime import date


def calculate_season_start_date(lease_start: date = None) -> date:
    """Return the date when the summer season starts

    If the current date is after the season end date,
    it returns next year's default start date.

    Leases always start on 10.6 the earliest
    """
    today = date.today()
    default = date(day=10, month=6, year=today.year)

    if lease_start:
        return default.replace(year=lease_start.year)

    # If today is gte than the date when all the leases end,
    # return the default start date for the next year
    if today >= date(day=14, month=9, year=today.year):
        return default.replace(year=today.year + 1)

    return default


def calculate_season_end_date(lease_end: date = None) -> date:
    """Return the date when the summer season ends

    Leases always end on 14.9, the year depends on the current year
    """
    today = date.today()
    default = date(day=14, month=9, year=today.year)

    if lease_end:
        return default.replace(year=lease_end.year)

    # If today is gte than the day when all leases end,
    # return the default end date for the next year
    if today >= default:
        return default.replace(year=today.year + 1)

    # Otherwise, return the default end date for the current year
    return default


def calculate_berth_lease_start_date() -> date:
    """
    Return the date when the lease season should start

    If a lease object is being created before 10.6, then the dates are in the same year.
    If the object is being created between those dates, then the start date is
    the date of creation and end date is 14.9 of the same year.
    If the object is being created after 14.9, then the dates are from next year.
    """

    # Otherwise, return the latest date between the default start date or today
    return max(calculate_season_start_date(), date.today())


def calculate_berth_lease_end_date() -> date:
    """Return the date when the lease season should end

    Leases always end on 14.9, the year depends on the current year
    """
    return calculate_season_end_date()
