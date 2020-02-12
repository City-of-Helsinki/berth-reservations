import pytest
from graphql_relay import to_global_id

from berth_reservations.tests.utils import (
    assert_not_enough_permissions,
    GraphQLTestClient,
)

client = GraphQLTestClient()

GRAPHQL_URL = "/graphql_v2/"

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
            id
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


def test_query_berth_leases(superuser, berth_lease, berth_application):
    berth_application.customer = berth_lease.customer
    berth_application.save()
    berth_lease.application = berth_application
    berth_lease.save()

    executed = client.execute(
        query=QUERY_BERTH_LEASES, graphql_url=GRAPHQL_URL, user=superuser,
    )

    berth_type_id = to_global_id("BerthTypeNode", berth_lease.berth.berth_type.id)
    berth_lease_id = to_global_id("BerthLeaseNode", berth_lease.id)
    berth_application_id = to_global_id("BerthApplicationNode", berth_application.id)
    customer_id = to_global_id("BerthProfileNode", berth_lease.customer.id)
    boat_id = str(berth_lease.boat.id)

    assert executed["data"]["berthLeases"]["edges"][0]["node"] == {
        "id": berth_lease_id,
        "status": "OFFERED",
        "startDate": str(berth_lease.start_date),
        "endDate": str(berth_lease.end_date),
        "comment": berth_lease.comment,
        "boat": {"id": boat_id},
        "customer": {"id": customer_id, "boats": [{"id": boat_id}]},
        "application": {"id": berth_application_id, "customer": {"id": customer_id}},
        "berth": {
            "id": to_global_id("BerthNode", berth_lease.berth.id),
            "number": str(berth_lease.berth.number),
            "berthType": {"id": berth_type_id},
        },
    }


@pytest.mark.parametrize("user", ["none", "base", "staff"], indirect=True)
def test_query_berth_leases_not_enough_permissions(user):
    executed = client.execute(
        query=QUERY_BERTH_LEASES, graphql_url=GRAPHQL_URL, user=user,
    )

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
        id
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


def test_query_berth_lease(superuser, berth_lease, berth_application):
    berth_lease_id = to_global_id("BerthLeaseNode", berth_lease.id)

    berth_application.customer = berth_lease.customer
    berth_application.save()
    berth_lease.application = berth_application
    berth_lease.save()

    query = QUERY_BERTH_LEASE % berth_lease_id
    executed = client.execute(query=query, graphql_url=GRAPHQL_URL, user=superuser,)

    berth_type_id = to_global_id("BerthTypeNode", berth_lease.berth.berth_type.id)
    berth_application_id = to_global_id("BerthApplicationNode", berth_application.id)
    customer_id = to_global_id("BerthProfileNode", berth_lease.customer.id)
    boat_id = str(berth_lease.boat.id)

    assert executed["data"]["berthLease"] == {
        "id": berth_lease_id,
        "status": "OFFERED",
        "startDate": str(berth_lease.start_date),
        "endDate": str(berth_lease.end_date),
        "comment": berth_lease.comment,
        "boat": {"id": boat_id},
        "customer": {"id": customer_id, "boats": [{"id": boat_id}]},
        "application": {"id": berth_application_id, "customer": {"id": customer_id}},
        "berth": {
            "id": to_global_id("BerthNode", berth_lease.berth.id),
            "number": str(berth_lease.berth.number),
            "berthType": {"id": berth_type_id},
        },
    }


@pytest.mark.parametrize("user", ["none", "base", "staff"], indirect=True)
def test_query_berth_lease_not_enough_permissions_valid_id(user, berth_lease):
    berth_lease_id = to_global_id("BerthLeaseNode", berth_lease.id)

    query = QUERY_BERTH_LEASE % berth_lease_id
    executed = client.execute(query=query, graphql_url=GRAPHQL_URL, user=user,)

    assert_not_enough_permissions(executed)


def test_query_berth_lease_invalid_id(user):
    executed = client.execute(
        query=QUERY_BERTH_LEASE, graphql_url=GRAPHQL_URL, user=user,
    )

    assert executed["data"]["berthLease"] is None
