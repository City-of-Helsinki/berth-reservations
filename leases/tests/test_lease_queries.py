import pytest
from dateutil.parser import isoparse
from freezegun import freeze_time
from graphql_relay import to_global_id

from applications.new_schema import BerthApplicationNode
from berth_reservations.tests.utils import assert_not_enough_permissions
from customers.schema import BoatNode, ProfileNode
from leases.schema import BerthLeaseNode
from leases.tests.factories import BerthLeaseFactory
from resources.schema import BerthNode, BerthTypeNode

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
                    berthType {
                        id
                    }
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

    berth_type_id = to_global_id(
        BerthTypeNode._meta.name, berth_lease.berth.berth_type.id
    )
    berth_lease_id = to_global_id(BerthLeaseNode._meta.name, berth_lease.id)
    berth_application_id = to_global_id(
        BerthApplicationNode._meta.name, berth_application.id
    )
    customer_id = to_global_id(ProfileNode._meta.name, berth_lease.customer.id)
    boat_id = to_global_id(BoatNode._meta.name, berth_lease.boat.id)

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
            "id": to_global_id(BerthNode._meta.name, berth_lease.berth.id),
            "number": str(berth_lease.berth.number),
            "berthType": {"id": berth_type_id},
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
            berthType {
                id
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
def test_query_berth_lease(api_client, berth_lease, berth_application):
    berth_lease_id = to_global_id(BerthLeaseNode._meta.name, berth_lease.id)

    berth_application.customer = berth_lease.customer
    berth_application.save()
    berth_lease.application = berth_application
    berth_lease.save()

    query = QUERY_BERTH_LEASE % berth_lease_id
    executed = api_client.execute(query)

    berth_type_id = to_global_id(
        BerthTypeNode._meta.name, berth_lease.berth.berth_type.id
    )
    berth_application_id = to_global_id(
        BerthApplicationNode._meta.name, berth_application.id
    )
    customer_id = to_global_id(ProfileNode._meta.name, berth_lease.customer.id)
    boat_id = to_global_id(BoatNode._meta.name, berth_lease.boat.id)

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
            "id": to_global_id(BerthNode._meta.name, berth_lease.berth.id),
            "number": str(berth_lease.berth.number),
            "berthType": {"id": berth_type_id},
        },
    }


@pytest.mark.parametrize(
    "api_client", ["api_client", "user", "harbor_services"], indirect=True
)
def test_query_berth_lease_not_enough_permissions_valid_id(api_client, berth_lease):
    berth_lease_id = to_global_id(BerthLeaseNode._meta.name, berth_lease.id)

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
