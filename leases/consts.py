from .enums import LeaseStatus

ACTIVE_LEASE_STATUSES = (
    LeaseStatus.DRAFTED,
    LeaseStatus.OFFERED,
    LeaseStatus.PAID,
    LeaseStatus.ERROR,
)
INACTIVE_LEASE_STATUSES = (LeaseStatus.REFUSED, LeaseStatus.EXPIRED)

# leases in "drafted" status are not to be set to terminated, instead they should be deleted from the database.
TERMINABLE_STATUSES = (LeaseStatus.OFFERED, LeaseStatus.PAID, LeaseStatus.ERROR)
