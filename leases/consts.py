from leases.enums import LeaseStatus

ACTIVE_LEASE_STATUSES = (LeaseStatus.DRAFTED, LeaseStatus.OFFERED, LeaseStatus.PAID)
INACTIVE_LEASE_STATUSES = (LeaseStatus.REFUSED, LeaseStatus.EXPIRED)
