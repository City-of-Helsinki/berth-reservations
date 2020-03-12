import pytest
from graphql_relay import to_global_id

from berth_reservations.tests.utils import assert_not_enough_permissions

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
                    berthType {
                        id
                    }
                }
            }
        }
    }
}
"""


def test_query_berth_leases(superuser_api_client, berth_lease, berth_application):
    berth_application.customer = berth_lease.customer
    berth_application.save()
    berth_lease.application = berth_application
    berth_lease.save()

    executed = superuser_api_client.execute(QUERY_BERTH_LEASES)

    berth_type_id = to_global_id("BerthTypeNode", berth_lease.berth.berth_type.id)
    berth_lease_id = to_global_id("BerthLeaseNode", berth_lease.id)
    berth_application_id = to_global_id("BerthApplicationNode", berth_application.id)
    customer_id = to_global_id("BerthProfileNode", berth_lease.customer.id)
    boat_id = to_global_id("BoatNode", berth_lease.boat.id)

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
            "id": to_global_id("BerthNode", berth_lease.berth.id),
            "number": str(berth_lease.berth.number),
            "berthType": {"id": berth_type_id},
        },
    }


@pytest.mark.parametrize(
    "api_client", ["api_client", "user_api_client", "staff_api_client"], indirect=True
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


def test_query_berth_lease(superuser_api_client, berth_lease, berth_application):
    berth_lease_id = to_global_id("BerthLeaseNode", berth_lease.id)

    berth_application.customer = berth_lease.customer
    berth_application.save()
    berth_lease.application = berth_application
    berth_lease.save()

    query = QUERY_BERTH_LEASE % berth_lease_id
    executed = superuser_api_client.execute(query)

    berth_type_id = to_global_id("BerthTypeNode", berth_lease.berth.berth_type.id)
    berth_application_id = to_global_id("BerthApplicationNode", berth_application.id)
    customer_id = to_global_id("BerthProfileNode", berth_lease.customer.id)
    boat_id = to_global_id("BoatNode", berth_lease.boat.id)

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
            "id": to_global_id("BerthNode", berth_lease.berth.id),
            "number": str(berth_lease.berth.number),
            "berthType": {"id": berth_type_id},
        },
    }


@pytest.mark.parametrize(
    "api_client", ["api_client", "user_api_client", "staff_api_client"], indirect=True
)
def test_query_berth_lease_not_enough_permissions_valid_id(api_client, berth_lease):
    berth_lease_id = to_global_id("BerthLeaseNode", berth_lease.id)

    query = QUERY_BERTH_LEASE % berth_lease_id

    executed = api_client.execute(query)

    assert_not_enough_permissions(executed)


def test_query_berth_lease_invalid_id(user_api_client):
    executed = user_api_client.execute(QUERY_BERTH_LEASE)

    assert executed["data"]["berthLease"] is None
