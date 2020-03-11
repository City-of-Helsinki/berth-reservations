import pytest
from graphql_relay import to_global_id

from applications.new_schema import BerthApplicationNode
from applications.tests.factories import BerthApplicationFactory
from berth_reservations.tests.utils import (
    assert_not_enough_permissions,
    create_api_client,
)
from leases.schema import BerthLeaseNode
from leases.tests.factories import BerthLeaseFactory

from ..schema import BerthProfileNode, BoatNode, ProfileNode
from ..tests.factories import BoatFactory, CompanyFactory

FEDERATED_SCHEMA_QUERY = """
    {
        _service {
            sdl
        }
    }
"""


def test_profile_node_gets_extended_properly(api_client):
    executed = api_client.execute(FEDERATED_SCHEMA_QUERY)
    assert (
        # TODO: remove the second "@key" when/if graphene-federartion fixes itself
        'extend type ProfileNode  implements Node  @key(fields: "id") '
        ' @key(fields: "id") {   id: ID! @external'
        in executed["data"]["_service"]["sdl"]
    )


FEDERATED_PROFILES_QUERY = """
query($_representations: [_Any!]!) {
    _entities(representations: $_representations) {
        ... on ProfileNode {
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
"""


def test_query_extended_profile_nodes(superuser_api_client, customer_profile):
    customer_profile_id = to_global_id(ProfileNode._meta.name, customer_profile.id)

    berth_application = BerthApplicationFactory(customer=customer_profile)
    berth_lease = BerthLeaseFactory(customer=customer_profile)
    company = CompanyFactory(customer=customer_profile)
    boat = BoatFactory(owner=customer_profile)

    variables = {
        "_representations": [
            {"id": customer_profile_id, "__typename": ProfileNode._meta.name}
        ]
    }

    executed = superuser_api_client.execute(
        FEDERATED_PROFILES_QUERY, variables=variables
    )

    boat_id = to_global_id(BoatNode._meta.name, boat.id)
    berth_application_id = to_global_id(
        BerthApplicationNode._meta.name, berth_application.id
    )
    berth_lease_id = to_global_id(BerthLeaseNode._meta.name, berth_lease.id)

    assert executed["data"]["_entities"][0] == {
        "id": customer_profile_id,
        "invoicingType": customer_profile.invoicing_type.name,
        "comment": customer_profile.comment,
        "company": {"businessId": company.business_id, "name": company.name},
        "boats": {"edges": [{"node": {"id": boat_id}}]},
        "berthApplications": {"edges": [{"node": {"id": berth_application_id}}]},
        "berthLeases": {"edges": [{"node": {"id": berth_lease_id}}]},
    }


@pytest.mark.parametrize(
    "api_client", ["api_client", "user_api_client", "staff_api_client"], indirect=True
)
def test_query_query_extended_profile_nodes_not_enough_permissions(
    api_client, customer_profile
):
    customer_profile_id = to_global_id(ProfileNode._meta.name, customer_profile.id)

    variables = {
        "_representations": [
            {"id": customer_profile_id, "__typename": ProfileNode._meta.name}
        ]
    }
    executed = api_client.execute(QUERY_BERTH_PROFILES, variables=variables)

    assert_not_enough_permissions(executed)


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


def test_query_berth_profiles(superuser_api_client, customer_profile):
    berth_application = BerthApplicationFactory(customer=customer_profile)
    berth_lease = BerthLeaseFactory(customer=customer_profile)
    company = CompanyFactory(customer=customer_profile)
    boat = BoatFactory(owner=customer_profile)

    executed = superuser_api_client.execute(QUERY_BERTH_PROFILES)

    customer_id = to_global_id(BerthProfileNode._meta.name, customer_profile.id)
    boat_id = to_global_id(BoatNode._meta.name, boat.id)
    berth_application_id = to_global_id(
        BerthApplicationNode._meta.name, berth_application.id
    )
    berth_lease_id = to_global_id(BerthLeaseNode._meta.name, berth_lease.id)

    assert executed["data"]["berthProfiles"]["edges"][0]["node"] == {
        "id": customer_id,
        "invoicingType": customer_profile.invoicing_type.name,
        "comment": customer_profile.comment,
        "company": {"businessId": company.business_id, "name": company.name},
        "boats": {"edges": [{"node": {"id": boat_id}}]},
        "berthApplications": {"edges": [{"node": {"id": berth_application_id}}]},
        "berthLeases": {"edges": [{"node": {"id": berth_lease_id}}]},
    }


@pytest.mark.parametrize(
    "api_client", ["api_client", "user_api_client", "staff_api_client"], indirect=True
)
def test_query_berth_profiles_not_enough_permissions(api_client):
    executed = api_client.execute(QUERY_BERTH_PROFILES)

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
def test_query_berth_profile(is_superuser, superuser_api_client, customer_profile):
    berth_profile_id = to_global_id(BerthProfileNode._meta.name, customer_profile.id)

    berth_application = BerthApplicationFactory(customer=customer_profile)
    berth_lease = BerthLeaseFactory(customer=customer_profile)
    company = CompanyFactory(customer=customer_profile)
    boat = BoatFactory(owner=customer_profile)

    query = QUERY_BERTH_PROFILE % berth_profile_id

    # only superusers and profile owners can see profile node info
    api_client = (
        superuser_api_client
        if is_superuser
        else create_api_client(customer_profile.user)
    )

    executed = api_client.execute(query)

    boat_id = to_global_id(BoatNode._meta.name, boat.id)
    berth_application_id = to_global_id(
        BerthApplicationNode._meta.name, berth_application.id
    )
    berth_lease_id = to_global_id(BerthLeaseNode._meta.name, berth_lease.id)

    assert executed["data"]["berthProfile"] == {
        "id": berth_profile_id,
        "invoicingType": customer_profile.invoicing_type.name,
        "comment": customer_profile.comment,
        "company": {"businessId": company.business_id, "name": company.name},
        "boats": {"edges": [{"node": {"id": boat_id}}]},
        "berthApplications": {"edges": [{"node": {"id": berth_application_id}}]},
        "berthLeases": {"edges": [{"node": {"id": berth_lease_id}}]},
    }


@pytest.mark.parametrize(
    "api_client", ["api_client", "user_api_client", "staff_api_client"], indirect=True
)
def test_query_berth_profile_not_enough_permissions_valid_id(
    api_client, customer_profile
):
    berth_profile_id = to_global_id(BerthProfileNode._meta.name, customer_profile.id)

    query = QUERY_BERTH_PROFILE % berth_profile_id

    executed = api_client.execute(query)

    assert_not_enough_permissions(executed)
