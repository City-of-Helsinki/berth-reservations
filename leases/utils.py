from datetime import date


# If a lease object is being created before 10.6, then the dates are in the same year.
# If the object is being created between those dates, then the start date is
# the date of creation and end date is 14.9 of the same year.
# If the object is being created after 14.9, then the dates are from next year.
def calculate_berth_lease_start_date():
    # Leases always start on 10.6 the earliest
    today = date.today()
    default = date(day=10, month=6, year=today.year)

    # If today is gte than the date when all the leases end,
    # return the default start date for the next year
    if today >= date(day=14, month=9, year=today.year):
        return default.replace(year=today.year + 1)

    # Otherwise, return the latest date between the default start date or today
    return max(default, today)


def calculate_berth_lease_end_date():
    # Leases always end on 14.9
    today = date.today()
    default = date(day=14, month=9, year=today.year)

    # If today is gte than the day when all leases end,
    # return the default end date for the next year
    if today >= default:
        return default.replace(year=today.year + 1)

    # Otherwise, return the default end date for the current year
    return default
