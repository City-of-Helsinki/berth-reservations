import random

import pytest
from dateutil.parser import isoparse
from freezegun import freeze_time

from applications.new_schema import BerthApplicationNode, WinterStorageApplicationNode
from berth_reservations.tests.utils import assert_not_enough_permissions
from customers.schema import BoatNode, ProfileNode
from payments.schema import OrderNode
from payments.tests.factories import (
    BerthProductFactory,
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
from ..schema import BerthLeaseNode, WinterStorageLeaseNode
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
                renewAutomatically
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
def test_query_berth_leases(api_client, berth_lease, berth_application):
    berth_application.customer = berth_lease.customer
    berth_application.save()
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
        "renewAutomatically": True,
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
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
def test_query_berth_lease(api_client, berth_lease, berth_application):
    berth_lease_id = to_global_id(BerthLeaseNode, berth_lease.id)

    berth_application.customer = berth_lease.customer
    berth_application.save()
    berth_lease.application = berth_application
    berth_lease.save()

    order = OrderFactory(
        lease=berth_lease, customer=berth_lease.customer, product=BerthProductFactory()
    )

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
def test_query_winter_storage_leases(api_client, place, winter_storage_application):
    if place:
        winter_storage_lease = WinterStorageLeaseFactory(
            place=WinterStoragePlaceFactory(), section=None
        )
    else:
        winter_storage_lease = WinterStorageLeaseFactory(
            place=None, section=WinterStorageSectionFactory()
        )

    winter_storage_application.customer = winter_storage_lease.customer
    winter_storage_application.save()
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
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
def test_query_winter_storage_lease(
    api_client, winter_storage_lease, winter_storage_application
):
    lease_id = to_global_id(WinterStorageLeaseNode, winter_storage_lease.id)

    winter_storage_application.customer = winter_storage_lease.customer
    winter_storage_application.save()
    winter_storage_lease.application = winter_storage_application
    winter_storage_lease.save()

    order = OrderFactory(
        lease=winter_storage_lease,
        customer=winter_storage_lease.customer,
        product=WinterStorageProductFactory(),
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
def test_query_winter_storage_leases_order_by_created_at_default(api_client):
    with freeze_time("2020-02-01"):
        WinterStorageLeaseFactory()

    with freeze_time("2020-01-01"):
        WinterStorageLeaseFactory()

    executed = api_client.execute(QUERY_WINTER_STORAGE_LEASES_CREATED_AT)

    first_date = isoparse(
        executed["data"]["winterStorageLeases"]["edges"][0]["node"]["createdAt"]
    )
    second_date = isoparse(
        executed["data"]["winterStorageLeases"]["edges"][1]["node"]["createdAt"]
    )

    assert first_date < second_date


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
