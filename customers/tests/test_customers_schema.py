import pytest
from graphql_relay import to_global_id

from applications.tests.factories import BerthApplicationFactory
from berth_reservations.tests.utils import (
    assert_not_enough_permissions,
    GraphQLTestClient,
)
from customers.tests.factories import BoatFactory, CompanyFactory
from leases.tests.factories import BerthLeaseFactory

client = GraphQLTestClient()

GRAPHQL_URL = "/graphql_v2/"


def test_profile_node_gets_extended_properly():
    query = """
        {
            _service {
                sdl
            }
        }
    """
    executed = client.execute(query=query, graphql_url=GRAPHQL_URL)
    assert (
        # TODO: remove the second "@key" when/if graphene-federartion fixes itself
        'extend type ProfileNode  implements Node  @key(fields: "id") '
        ' @key(fields: "id") {   id: ID! @external'
        in executed["data"]["_service"]["sdl"]
    )


QUERY_BERTH_PROFILES = """
query GetBerthProfiles {
    berthProfiles {
        edges {
            node {
                id
                invoicingType
                comment
                company {
                    businessId
                    name
                }
                boats {
                    edges {
                        node {
                            id
                        }
                    }
                }
                berthApplications {
                    edges {
                        node {
                            id
                        }
                    }
                }
                berthLeases {
                    edges {
                        node {
                            id
                        }
                    }
                }
            }
        }
    }
}
"""


def test_query_berth_profiles(superuser, customer_profile):
    berth_application = BerthApplicationFactory(customer=customer_profile)
    berth_lease = BerthLeaseFactory(customer=customer_profile)
    company = CompanyFactory(customer=customer_profile)
    boat = BoatFactory(owner=customer_profile)

    executed = client.execute(
        query=QUERY_BERTH_PROFILES, graphql_url=GRAPHQL_URL, user=superuser,
    )

    customer_id = to_global_id("BerthProfileNode", customer_profile.id)
    boat_id = to_global_id("BoatNode", boat.id)
    berth_application_id = to_global_id("BerthApplicationNode", berth_application.id)
    berth_lease_id = to_global_id("BerthLeaseNode", berth_lease.id)

    assert executed["data"]["berthProfiles"]["edges"][0]["node"] == {
        "id": customer_id,
        "invoicingType": customer_profile.invoicing_type.name,
        "comment": customer_profile.comment,
        "company": {"businessId": company.business_id, "name": company.name},
        "boats": {"edges": [{"node": {"id": boat_id}}]},
        "berthApplications": {"edges": [{"node": {"id": berth_application_id}}]},
        "berthLeases": {"edges": [{"node": {"id": berth_lease_id}}]},
    }


@pytest.mark.parametrize("user", ["none", "base", "staff"], indirect=True)
def test_query_berth_profiles_not_enough_permissions(user):
    executed = client.execute(
        query=QUERY_BERTH_PROFILES, graphql_url=GRAPHQL_URL, user=user,
    )

    assert_not_enough_permissions(executed)


QUERY_BERTH_PROFILE = """
query GetBerthProfile {
    berthProfile(id: "%s") {
        id
        invoicingType
        comment
        company {
            businessId
            name
        }
        boats {
            edges {
                node {
                    id
                }
            }
        }
        berthApplications {
            edges {
                node {
                    id
                }
            }
        }
        berthLeases {
            edges {
                node {
                    id
                }
            }
        }
    }
}
"""


@pytest.mark.parametrize("is_superuser", [True, False])
def test_query_berth_profile(is_superuser, superuser, customer_profile):
    berth_profile_id = to_global_id("BerthProfileNode", customer_profile.id)

    berth_application = BerthApplicationFactory(customer=customer_profile)
    berth_lease = BerthLeaseFactory(customer=customer_profile)
    company = CompanyFactory(customer=customer_profile)
    boat = BoatFactory(owner=customer_profile)

    query = QUERY_BERTH_PROFILE % berth_profile_id

    # only superusers and profile owners can see profile node info
    gql_user = superuser if is_superuser else customer_profile.user

    executed = client.execute(query=query, graphql_url=GRAPHQL_URL, user=gql_user)

    boat_id = to_global_id("BoatNode", boat.id)
    berth_application_id = to_global_id("BerthApplicationNode", berth_application.id)
    berth_lease_id = to_global_id("BerthLeaseNode", berth_lease.id)

    assert executed["data"]["berthProfile"] == {
        "id": berth_profile_id,
        "invoicingType": customer_profile.invoicing_type.name,
        "comment": customer_profile.comment,
        "company": {"businessId": company.business_id, "name": company.name},
        "boats": {"edges": [{"node": {"id": boat_id}}]},
        "berthApplications": {"edges": [{"node": {"id": berth_application_id}}]},
        "berthLeases": {"edges": [{"node": {"id": berth_lease_id}}]},
    }


@pytest.mark.parametrize("user", ["none", "base", "staff"], indirect=True)
def test_query_berth_profile_not_enough_permissions_valid_id(user, customer_profile):
    berth_profile_id = to_global_id("BerthProfileNode", customer_profile.id)

    query = QUERY_BERTH_PROFILE % berth_profile_id
    executed = client.execute(query=query, graphql_url=GRAPHQL_URL, user=user)

    assert_not_enough_permissions(executed)
