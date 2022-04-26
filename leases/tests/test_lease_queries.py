import random
from datetime import date

import pytest
from dateutil.parser import isoparse
from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from freezegun import freeze_time

from applications.schema import BerthApplicationNode, WinterStorageApplicationNode
from applications.tests.factories import (
    BerthApplicationFactory,
    WinterStorageApplicationFactory,
)
from berth_reservations.tests.utils import (
    assert_not_enough_permissions,
    create_api_client,
)
from contracts.schema.types import BerthContractNode, WinterStorageContractNode
from contracts.tests.factories import BerthContractFactory, WinterStorageContractFactory
from customers.schema import BoatNode, ProfileNode
from payments.enums import OfferStatus
from payments.schema import OrderNode
from payments.tests.factories import (
    BerthProductFactory,
    BerthSwitchOfferFactory,
    OrderFactory,
    WinterStorageProductFactory,
)
from resources.schema import BerthNode, WinterStoragePlaceNode, WinterStorageSectionNode
from resources.tests.factories import (
    WinterStoragePlaceFactory,
    WinterStorageSectionFactory,
)
from utils.relay import to_global_id

from ..enums import LeaseStatus
from ..models import BerthLease
from ..schema import BerthLeaseNode, WinterStorageLeaseNode
from ..utils import (
    calculate_season_end_date,
    calculate_season_start_date,
    calculate_winter_season_end_date,
    calculate_winter_season_start_date,
)
from .factories import BerthLeaseFactory, WinterStorageLeaseFactory

QUERY_BERTH_LEASES = """
query GetBerthLeases {
    berthLeases {
        edges {
            node {
                id
                status
                startDate
                endDate
                comment
                boat {
                    id
                }
                customer {
                    id
                    boats {
                        edges {
                            node {
                                id
                            }
                        }
                    }
                }
                application {
                    id
                    customer {
                        id
                    }
                }
                berth {
                    id
                    number
                }
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
def test_query_berth_leases(api_client, berth_lease):
    berth_application = BerthApplicationFactory(
        customer=berth_lease.customer, boat=berth_lease.boat
    )
    berth_lease.application = berth_application
    berth_lease.save()

    executed = api_client.execute(QUERY_BERTH_LEASES)

    berth_lease_id = to_global_id(BerthLeaseNode, berth_lease.id)
    berth_application_id = to_global_id(BerthApplicationNode, berth_application.id)
    customer_id = to_global_id(ProfileNode, berth_lease.customer.id)
    boat_id = to_global_id(BoatNode, berth_lease.boat.id)

    assert executed["data"]["berthLeases"]["edges"][0]["node"] == {
        "id": berth_lease_id,
        "status": "DRAFTED",
        "startDate": str(berth_lease.start_date),
        "endDate": str(berth_lease.end_date),
        "comment": berth_lease.comment,
        "boat": {"id": boat_id},
        "customer": {
            "id": customer_id,
            "boats": {"edges": [{"node": {"id": boat_id}}]},
        },
        "application": {"id": berth_application_id, "customer": {"id": customer_id}},
        "berth": {
            "id": to_global_id(BerthNode, berth_lease.berth.id),
            "number": berth_lease.berth.number,
        },
    }


@pytest.mark.parametrize(
    "api_client", ["api_client", "user", "harbor_services"], indirect=True
)
def test_query_berth_leases_not_enough_permissions(api_client):
    executed = api_client.execute(QUERY_BERTH_LEASES)

    assert_not_enough_permissions(executed)


QUERY_BERTH_LEASE = """
query GetBerthLease {
    berthLease(id: "%s") {
        id
        status
        startDate
        endDate
        comment
        boat {
            id
        }
        customer {
            id
            boats {
                edges {
                    node {
                        id
                    }
                }
            }
        }
        application {
            id
            customer {
                id
            }
        }
        berth {
            id
            number
        }
        order {
            id
        }
        contract {
            id
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
def test_query_berth_lease(api_client, berth_lease):
    berth_lease_id = to_global_id(BerthLeaseNode, berth_lease.id)

    berth_application = BerthApplicationFactory(
        customer=berth_lease.customer, boat=berth_lease.boat
    )
    berth_lease.contract = BerthContractFactory()
    berth_lease.contract.save()
    berth_lease.application = berth_application
    berth_lease.save()

    order = OrderFactory(lease=berth_lease)

    query = QUERY_BERTH_LEASE % berth_lease_id
    executed = api_client.execute(query)

    berth_application_id = to_global_id(BerthApplicationNode, berth_application.id)
    customer_id = to_global_id(ProfileNode, berth_lease.customer.id)
    boat_id = to_global_id(BoatNode, berth_lease.boat.id)

    assert executed["data"]["berthLease"] == {
        "id": berth_lease_id,
        "status": "DRAFTED",
        "startDate": str(berth_lease.start_date),
        "endDate": str(berth_lease.end_date),
        "comment": berth_lease.comment,
        "boat": {"id": boat_id},
        "customer": {
            "id": customer_id,
            "boats": {"edges": [{"node": {"id": boat_id}}]},
        },
        "application": {"id": berth_application_id, "customer": {"id": customer_id}},
        "berth": {
            "id": to_global_id(BerthNode, berth_lease.berth.id),
            "number": berth_lease.berth.number,
        },
        "order": {"id": to_global_id(OrderNode, order.id)},
        "contract": {"id": to_global_id(BerthContractNode, berth_lease.contract.id)},
    }


@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
def test_query_berth_lease_with_switch_offer_customer(api_client, berth_lease):
    berth_lease.status = LeaseStatus.PAID
    berth_lease.save()
    berth_lease_id = to_global_id(BerthLeaseNode, berth_lease.id)
    customer_id = to_global_id(ProfileNode, berth_lease.customer.id)
    BerthSwitchOfferFactory(
        lease=berth_lease,
        customer=berth_lease.customer,
        status=OfferStatus.OFFERED,
        due_date=date.today(),
    )

    query = (
        """
        {
            berthLease(id: "%s") {
              id
              switchOfferCustomer {
                id
              }
            }
        }
    """
        % berth_lease_id
    )
    executed = api_client.execute(query)

    assert executed["data"]["berthLease"] == {
        "id": berth_lease_id,
        "switchOfferCustomer": {"id": customer_id},
    }


@pytest.mark.parametrize(
    "api_client", ["api_client", "user", "harbor_services"], indirect=True
)
def test_query_berth_lease_not_enough_permissions_valid_id(api_client, berth_lease):
    berth_lease_id = to_global_id(BerthLeaseNode, berth_lease.id)

    query = QUERY_BERTH_LEASE % berth_lease_id

    executed = api_client.execute(query)

    assert_not_enough_permissions(executed)


def test_query_berth_lease_invalid_id(superuser_api_client):
    executed = superuser_api_client.execute(QUERY_BERTH_LEASE)

    assert executed["data"]["berthLease"] is None


BERTH_LEASES_WITH_ORDER_BY = """
query LEASES {
    berthLeases(orderBy: "%s") {
        edges {
            node {
                createdAt
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "order_by,ascending", [("createdAt", True), ("-createdAt", False)]
)
@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
def test_query_berth_leases_order_by_created_at(order_by, ascending, api_client):
    with freeze_time("2020-02-01"):
        BerthLeaseFactory()

    with freeze_time("2020-01-01"):
        BerthLeaseFactory()

    query = BERTH_LEASES_WITH_ORDER_BY % order_by

    executed = api_client.execute(query)

    first_date = isoparse(
        executed["data"]["berthLeases"]["edges"][0 if ascending else 1]["node"][
            "createdAt"
        ]
    )
    second_date = isoparse(
        executed["data"]["berthLeases"]["edges"][1 if ascending else 0]["node"][
            "createdAt"
        ]
    )

    assert first_date < second_date


QUERY_BERTH_LEASE_CREATED_AT = """
query BerthLeaseCreatedAt {
    berthLeases {
        edges {
            node {
                createdAt
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
def test_query_berth_leases_order_by_created_at_default(api_client):
    with freeze_time("2020-02-01"):
        BerthLeaseFactory()

    with freeze_time("2020-01-01"):
        BerthLeaseFactory()

    executed = api_client.execute(QUERY_BERTH_LEASE_CREATED_AT)

    first_date = isoparse(
        executed["data"]["berthLeases"]["edges"][0]["node"]["createdAt"]
    )
    second_date = isoparse(
        executed["data"]["berthLeases"]["edges"][1]["node"]["createdAt"]
    )

    assert first_date < second_date


def test_query_berth_lease_count(superuser_api_client):
    count = random.randint(1, 10)
    for _i in range(count):
        BerthLeaseFactory()

    query = """
        {
            berthLeases {
                count
                totalCount
            }
        }
    """

    executed = superuser_api_client.execute(query)
    assert executed["data"] == {"berthLeases": {"count": count, "totalCount": count}}


QUERY_WINTER_STORAGE_LEASES = """
query GetWinterStorageLeases {
    winterStorageLeases {
        edges {
            node {
                id
                status
                startDate
                endDate
                comment
                boat {
                    id
                }
                customer {
                    id
                    boats {
                        edges {
                            node {
                                id
                            }
                        }
                    }
                }
                application {
                    id
                    customer {
                        id
                    }
                }
                place {
                    id
                }
                section {
                    id
                }
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
@pytest.mark.parametrize("place", [True, False])
def test_query_winter_storage_leases(api_client, place):
    if place:
        winter_storage_lease = WinterStorageLeaseFactory(
            place=WinterStoragePlaceFactory(), section=None
        )
    else:
        winter_storage_lease = WinterStorageLeaseFactory(
            place=None, section=WinterStorageSectionFactory()
        )

    winter_storage_application = WinterStorageApplicationFactory(
        customer=winter_storage_lease.customer, boat=winter_storage_lease.boat
    )
    winter_storage_lease.application = winter_storage_application
    winter_storage_lease.save()

    executed = api_client.execute(QUERY_WINTER_STORAGE_LEASES)

    lease_id = to_global_id(WinterStorageLeaseNode, winter_storage_lease.id)
    application_id = to_global_id(
        WinterStorageApplicationNode, winter_storage_application.id
    )
    customer_id = to_global_id(ProfileNode, winter_storage_lease.customer.id)
    boat_id = to_global_id(BoatNode, winter_storage_lease.boat.id)

    place_dict = {
        "place": {
            "id": to_global_id(WinterStoragePlaceNode, winter_storage_lease.place.id),
        }
        if place
        else None,
        "section": {
            "id": to_global_id(
                WinterStorageSectionNode, winter_storage_lease.section.id
            ),
        }
        if not place
        else None,
    }

    assert executed["data"]["winterStorageLeases"]["edges"][0]["node"] == {
        "id": lease_id,
        "status": "DRAFTED",
        "startDate": str(winter_storage_lease.start_date),
        "endDate": str(winter_storage_lease.end_date),
        "comment": winter_storage_lease.comment,
        "boat": {"id": boat_id},
        "customer": {
            "id": customer_id,
            "boats": {"edges": [{"node": {"id": boat_id}}]},
        },
        "application": {"id": application_id, "customer": {"id": customer_id}},
        **place_dict,
    }


@pytest.mark.parametrize(
    "api_client", ["api_client", "user", "harbor_services"], indirect=True
)
def test_query_winter_storage_leases_not_enough_permissions(api_client):
    executed = api_client.execute(QUERY_WINTER_STORAGE_LEASES)

    assert_not_enough_permissions(executed)


QUERY_WINTER_STORAGE_LEASE = """
query GetWinterStorageLease {
    winterStorageLease(id: "%s") {
        id
        status
        startDate
        endDate
        comment
        boat {
            id
        }
        customer {
            id
            boats {
                edges {
                    node {
                        id
                    }
                }
            }
        }
        application {
            id
            customer {
                id
            }
        }
        place {
            id
        }
        order {
            id
        }
        contract {
            id
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
def test_query_winter_storage_lease(api_client, winter_storage_lease):
    winter_storage_application = WinterStorageApplicationFactory(
        customer=winter_storage_lease.customer, boat=winter_storage_lease.boat
    )
    lease_id = to_global_id(WinterStorageLeaseNode, winter_storage_lease.id)

    winter_storage_lease.contract = WinterStorageContractFactory()
    winter_storage_lease.contract.save()
    winter_storage_lease.application = winter_storage_application
    winter_storage_lease.save()

    order = OrderFactory(
        lease=winter_storage_lease,
    )

    query = QUERY_WINTER_STORAGE_LEASE % lease_id
    executed = api_client.execute(query)

    application_id = to_global_id(
        WinterStorageApplicationNode, winter_storage_application.id
    )
    customer_id = to_global_id(ProfileNode, winter_storage_lease.customer.id)
    boat_id = to_global_id(BoatNode, winter_storage_lease.boat.id)

    assert executed["data"]["winterStorageLease"] == {
        "id": lease_id,
        "status": "DRAFTED",
        "startDate": str(winter_storage_lease.start_date),
        "endDate": str(winter_storage_lease.end_date),
        "comment": winter_storage_lease.comment,
        "boat": {"id": boat_id},
        "customer": {
            "id": customer_id,
            "boats": {"edges": [{"node": {"id": boat_id}}]},
        },
        "application": {"id": application_id, "customer": {"id": customer_id}},
        "place": {
            "id": to_global_id(WinterStoragePlaceNode, winter_storage_lease.place.id),
        },
        "order": {"id": to_global_id(OrderNode, order.id)},
        "contract": {
            "id": to_global_id(
                WinterStorageContractNode, winter_storage_lease.contract.id
            )
        },
    }


@pytest.mark.parametrize(
    "api_client", ["api_client", "user", "harbor_services"], indirect=True
)
def test_query_winter_storage_lease_not_enough_permissions_valid_id(
    api_client, winter_storage_lease
):
    lease_id = to_global_id(WinterStorageLeaseNode, winter_storage_lease.id)

    query = QUERY_WINTER_STORAGE_LEASE % lease_id

    executed = api_client.execute(query)

    assert_not_enough_permissions(executed)


def test_query_winter_storage_lease_invalid_id(superuser_api_client):
    executed = superuser_api_client.execute(QUERY_WINTER_STORAGE_LEASE)

    assert executed["data"]["winterStorageLease"] is None


QUERY_WINTER_STORAGE_LEASES_WITH_ORDER_BY = """
query LEASES {
    winterStorageLeases(orderBy: "%s") {
        edges {
            node {
                createdAt
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "order_by,ascending", [("createdAt", True), ("-createdAt", False)]
)
@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
def test_query_winter_storage_leases_order_by_created_at(
    order_by, ascending, api_client
):
    with freeze_time("2020-02-01"):
        WinterStorageLeaseFactory()

    with freeze_time("2020-01-01"):
        WinterStorageLeaseFactory()

    query = QUERY_WINTER_STORAGE_LEASES_WITH_ORDER_BY % order_by

    executed = api_client.execute(query)

    first_date = isoparse(
        executed["data"]["winterStorageLeases"]["edges"][0 if ascending else 1]["node"][
            "createdAt"
        ]
    )
    second_date = isoparse(
        executed["data"]["winterStorageLeases"]["edges"][1 if ascending else 0]["node"][
            "createdAt"
        ]
    )

    assert first_date < second_date


QUERY_WINTER_STORAGE_LEASES_CREATED_AT = """
query WinterStorageLeaseCreatedAt {
    winterStorageLeases {
        edges {
            node {
                createdAt
                startDate
                endDate
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
def test_query_winter_storage_leases_order_by_start_date_default(api_client):
    with freeze_time("2020-01-01"):
        WinterStorageLeaseFactory()

    with freeze_time("2021-01-01"):
        WinterStorageLeaseFactory()

    executed = api_client.execute(QUERY_WINTER_STORAGE_LEASES_CREATED_AT)

    first_date = isoparse(
        executed["data"]["winterStorageLeases"]["edges"][0]["node"]["startDate"]
    )
    second_date = isoparse(
        executed["data"]["winterStorageLeases"]["edges"][1]["node"]["startDate"]
    )

    assert first_date > second_date


def test_query_winter_storage_lease_count(superuser_api_client):
    count = random.randint(1, 10)
    for _i in range(count):
        WinterStorageLeaseFactory()

    query = """
        {
            winterStorageLeases {
                count
                totalCount
            }
        }
    """

    executed = superuser_api_client.execute(query)
    assert executed["data"] == {
        "winterStorageLeases": {"count": count, "totalCount": count}
    }


FILTERED_QUERY_BERTH_LEASES = """
query GetBerthLeases {
    berthLeases(statuses: [%s], startYear: %d) {
        edges {
            node {
                id
                status
                startDate
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
@freeze_time("2020-02-01")
def test_query_berth_leases_filtered(api_client):
    berth_lease = BerthLeaseFactory(status=LeaseStatus.DRAFTED)
    query = FILTERED_QUERY_BERTH_LEASES % ("DRAFTED", 2020)

    berth_lease_id = to_global_id(BerthLeaseNode, berth_lease.id)

    executed = api_client.execute(query)

    assert executed["data"]["berthLeases"]["edges"][0]["node"] == {
        "id": berth_lease_id,
        "status": "DRAFTED",
        "startDate": str(berth_lease.start_date),
    }


QUERY_SEND_BERTH_INVOICE_PREVIEW = """
query SendBerthInvoicePreview {
    sendBerthInvoicePreview {
        expectedLeases
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
@freeze_time("2020-02-01")
def test_query_send_berth_invoice_preview(api_client):
    lease = BerthLeaseFactory(
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_season_start_date(today() - relativedelta(years=1)),
        end_date=calculate_season_end_date(today() - relativedelta(years=1)),
    )
    lease.contract = BerthContractFactory()
    lease.contract.save()
    BerthLeaseFactory(
        boat=None,
        status=LeaseStatus.REFUSED,
        start_date=calculate_season_start_date(today() - relativedelta(years=1)),
        end_date=calculate_season_end_date(today() - relativedelta(years=1)),
    )
    BerthProductFactory(
        min_width=lease.berth.berth_type.width - 1,
        max_width=lease.berth.berth_type.width + 1,
    )

    executed = api_client.execute(QUERY_SEND_BERTH_INVOICE_PREVIEW)

    assert executed["data"]["sendBerthInvoicePreview"] == {"expectedLeases": 1}


FILTERED_QUERY_WINTER_STORAGE_LEASES = """
query GetWinterStorageLeases {
    winterStorageLeases(statuses: [%s], startYear: %d) {
        edges {
            node {
                id
                status
                startDate
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
@freeze_time("2020-02-01")
def test_query_winter_storage_leases_filtered(api_client):
    lease = WinterStorageLeaseFactory(status=LeaseStatus.DRAFTED)
    WinterStorageLeaseFactory(status=LeaseStatus.OFFERED)

    query = FILTERED_QUERY_WINTER_STORAGE_LEASES % ("DRAFTED", 2020)

    lease_id = to_global_id(WinterStorageLeaseNode, lease.id)

    executed = api_client.execute(query)

    assert executed["data"]["winterStorageLeases"]["edges"][0]["node"] == {
        "id": lease_id,
        "status": "DRAFTED",
        "startDate": str(lease.start_date),
    }


QUERY_SEND_WINTER_STORAGE_LEASE_INVOICE_PREVIEW = """
query SendWinterStorageInvoicePreview {
    sendMarkedWinterStorageInvoicePreview  {
        expectedLeases
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
@freeze_time("2020-01-01")
def test_query_send_marked_winter_storage_invoice_preview(api_client):
    lease = WinterStorageLeaseFactory(
        boat=None,
        status=LeaseStatus.PAID,
        start_date=calculate_winter_season_start_date(),
        end_date=calculate_winter_season_end_date(),
    )
    WinterStorageLeaseFactory(
        boat=None,
        status=LeaseStatus.REFUSED,
        start_date=calculate_winter_season_start_date(),
        end_date=calculate_winter_season_end_date(),
    )
    WinterStorageProductFactory(
        winter_storage_area=lease.place.winter_storage_section.area
    )

    executed = api_client.execute(QUERY_SEND_WINTER_STORAGE_LEASE_INVOICE_PREVIEW)

    assert executed["data"]["sendMarkedWinterStorageInvoicePreview"] == {
        "expectedLeases": 1
    }


# Test added specifically to be sure that the sending of invoices on 17.8.21 would work
@freeze_time("2021-08-17")
def test_query_send_marked_winter_storage_invoice_preview_2021_08_17(
    superuser_api_client,
):
    lease = WinterStorageLeaseFactory(
        boat=None,
        status=LeaseStatus.PAID,
        start_date="2020-09-15",
        end_date="2021-06-10",
    )
    WinterStorageLeaseFactory(
        boat=None,
        status=LeaseStatus.REFUSED,
        start_date="2020-09-15",
        end_date="2021-06-10",
    )
    WinterStorageProductFactory(
        winter_storage_area=lease.place.winter_storage_section.area
    )

    executed = superuser_api_client.execute(
        QUERY_SEND_WINTER_STORAGE_LEASE_INVOICE_PREVIEW
    )

    assert executed["data"]["sendMarkedWinterStorageInvoicePreview"] == {
        "expectedLeases": 1
    }


CUSTOMER_OWN_BERTH_LEASES_QUERY = """
query BERTH_LEASES {
    berthLeases {
        edges {
            node {
                id
                customer {
                    id
                }
            }
        }
    }
}
"""


def test_get_customer_own_berth_leases(customer_profile):
    customer_lease = BerthLeaseFactory(customer=customer_profile)
    BerthLeaseFactory()

    api_client = create_api_client(user=customer_profile.user)
    executed = api_client.execute(CUSTOMER_OWN_BERTH_LEASES_QUERY)

    assert BerthLease.objects.count() == 2

    assert len(executed["data"]["berthLeases"]["edges"]) == 1
    assert executed["data"]["berthLeases"]["edges"][0]["node"] == {
        "id": to_global_id(BerthLeaseNode, customer_lease.id),
        "customer": {"id": to_global_id(ProfileNode, customer_profile.id)},
    }
