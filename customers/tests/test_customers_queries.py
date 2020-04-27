import pytest

from applications.new_schema import BerthApplicationNode
from applications.tests.factories import BerthApplicationFactory
from berth_reservations.tests.utils import (
    assert_not_enough_permissions,
    create_api_client,
)
from leases.schema import BerthLeaseNode
from leases.tests.factories import BerthLeaseFactory
from utils.relay import to_global_id

from ..schema import BerthProfileNode, BoatCertificateNode, BoatNode, ProfileNode
from ..tests.factories import BoatFactory, OrganizationFactory

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
            organization {
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


@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
def test_query_extended_profile_nodes(api_client, customer_profile):
    customer_profile_id = to_global_id(ProfileNode, customer_profile.id)

    berth_application = BerthApplicationFactory(customer=customer_profile)
    berth_lease = BerthLeaseFactory(customer=customer_profile)
    organization = OrganizationFactory(customer=customer_profile)
    boat = BoatFactory(owner=customer_profile)

    variables = {
        "_representations": [
            {"id": customer_profile_id, "__typename": ProfileNode._meta.name}
        ]
    }

    executed = api_client.execute(FEDERATED_PROFILES_QUERY, variables=variables)

    boat_id = to_global_id(BoatNode, boat.id)
    berth_application_id = to_global_id(BerthApplicationNode, berth_application.id)
    berth_lease_id = to_global_id(BerthLeaseNode, berth_lease.id)

    assert executed["data"]["_entities"][0] == {
        "id": customer_profile_id,
        "invoicingType": customer_profile.invoicing_type.name,
        "comment": customer_profile.comment,
        "organization": {
            "businessId": organization.business_id,
            "name": organization.name,
        },
        "boats": {"edges": [{"node": {"id": boat_id}}]},
        "berthApplications": {"edges": [{"node": {"id": berth_application_id}}]},
        "berthLeases": {"edges": [{"node": {"id": berth_lease_id}}]},
    }


@pytest.mark.parametrize(
    "api_client", ["api_client", "user", "harbor_services"], indirect=True
)
def test_query_query_extended_profile_nodes_not_enough_permissions(
    api_client, customer_profile
):
    customer_profile_id = to_global_id(ProfileNode, customer_profile.id)

    variables = {
        "_representations": [{"id": customer_profile_id, "__typename": ProfileNode}]
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
                organization {
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


@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
def test_query_berth_profiles(api_client, customer_profile):
    berth_application = BerthApplicationFactory(customer=customer_profile)
    berth_lease = BerthLeaseFactory(customer=customer_profile)
    organization = OrganizationFactory(customer=customer_profile)
    boat = BoatFactory(owner=customer_profile)

    executed = api_client.execute(QUERY_BERTH_PROFILES)

    customer_id = to_global_id(BerthProfileNode, customer_profile.id)
    boat_id = to_global_id(BoatNode, boat.id)
    berth_application_id = to_global_id(BerthApplicationNode, berth_application.id)
    berth_lease_id = to_global_id(BerthLeaseNode, berth_lease.id)

    assert executed["data"]["berthProfiles"]["edges"][0]["node"] == {
        "id": customer_id,
        "invoicingType": customer_profile.invoicing_type.name,
        "comment": customer_profile.comment,
        "organization": {
            "businessId": organization.business_id,
            "name": organization.name,
        },
        "boats": {"edges": [{"node": {"id": boat_id}}]},
        "berthApplications": {"edges": [{"node": {"id": berth_application_id}}]},
        "berthLeases": {"edges": [{"node": {"id": berth_lease_id}}]},
    }


@pytest.mark.parametrize(
    "api_client", ["api_client", "user", "harbor_services"], indirect=True
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
        organization {
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


@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
def test_query_berth_profile(api_client, customer_profile):
    berth_profile_id = to_global_id(BerthProfileNode, customer_profile.id)

    berth_application = BerthApplicationFactory(customer=customer_profile)
    berth_lease = BerthLeaseFactory(customer=customer_profile)
    organization = OrganizationFactory(customer=customer_profile)
    boat = BoatFactory(owner=customer_profile)

    query = QUERY_BERTH_PROFILE % berth_profile_id

    executed = api_client.execute(query)

    boat_id = to_global_id(BoatNode, boat.id)
    berth_application_id = to_global_id(BerthApplicationNode, berth_application.id)
    berth_lease_id = to_global_id(BerthLeaseNode, berth_lease.id)

    assert executed["data"]["berthProfile"] == {
        "id": berth_profile_id,
        "invoicingType": customer_profile.invoicing_type.name,
        "comment": customer_profile.comment,
        "organization": {
            "businessId": organization.business_id,
            "name": organization.name,
        },
        "boats": {"edges": [{"node": {"id": boat_id}}]},
        "berthApplications": {"edges": [{"node": {"id": berth_application_id}}]},
        "berthLeases": {"edges": [{"node": {"id": berth_lease_id}}]},
    }


def test_query_berth_profile_self_user(customer_profile):
    berth_profile_id = to_global_id(BerthProfileNode, customer_profile.id)

    berth_application = BerthApplicationFactory(customer=customer_profile)
    berth_lease = BerthLeaseFactory(customer=customer_profile)
    organization = OrganizationFactory(customer=customer_profile)
    boat = BoatFactory(owner=customer_profile)

    query = QUERY_BERTH_PROFILE % berth_profile_id

    api_client = create_api_client(user=customer_profile.user)
    executed = api_client.execute(query)

    boat_id = to_global_id(BoatNode, boat.id)
    berth_application_id = to_global_id(BerthApplicationNode, berth_application.id)
    berth_lease_id = to_global_id(BerthLeaseNode, berth_lease.id)

    assert executed["data"]["berthProfile"] == {
        "id": berth_profile_id,
        "invoicingType": customer_profile.invoicing_type.name,
        "comment": customer_profile.comment,
        "organization": {
            "businessId": organization.business_id,
            "name": organization.name,
        },
        "boats": {"edges": [{"node": {"id": boat_id}}]},
        "berthApplications": {"edges": [{"node": {"id": berth_application_id}}]},
        "berthLeases": {"edges": [{"node": {"id": berth_lease_id}}]},
    }


@pytest.mark.parametrize(
    "api_client", ["user", "harbor_services"], indirect=True,
)
def test_query_berth_profile_not_enough_permissions_valid_id(
    api_client, customer_profile
):
    berth_profile_id = to_global_id(BerthProfileNode, customer_profile.id)

    query = QUERY_BERTH_PROFILE % berth_profile_id

    executed = api_client.execute(query)

    assert_not_enough_permissions(executed)


QUERY_BOAT_CERTIFICATES = """
query BOATS_CERTIFICATES {
    berthProfile(id: "%s") {
        id
        boats {
            edges {
                node {
                    id
                    certificates {
                        id
                    }
                }
            }
        }
    }
}
"""


def test_query_boat_certificates(superuser_api_client, boat_certificate):
    certificate_id = to_global_id(BoatCertificateNode, boat_certificate.id)
    boat_id = to_global_id(BoatNode, boat_certificate.boat.id)
    customer_id = to_global_id(BerthProfileNode, boat_certificate.boat.owner.id)

    query = QUERY_BOAT_CERTIFICATES % customer_id

    executed = superuser_api_client.execute(query)

    assert executed["data"]["berthProfile"] == {
        "id": customer_id,
        "boats": {
            "edges": [
                {"node": {"id": boat_id, "certificates": [{"id": certificate_id}]}}
            ]
        },
    }
