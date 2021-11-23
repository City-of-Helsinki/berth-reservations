import random

import pytest
from dateutil.parser import isoparse
from freezegun import freeze_time

from applications.schema import BerthApplicationNode, WinterStorageApplicationNode
from applications.tests.factories import (
    BerthApplicationFactory,
    WinterStorageApplicationFactory,
)
from berth_reservations.tests.factories import CustomerProfileFactory
from berth_reservations.tests.utils import (
    assert_not_enough_permissions,
    create_api_client,
)
from leases.enums import LeaseStatus
from leases.schema import BerthLeaseNode, WinterStorageLeaseNode
from leases.tests.factories import BerthLeaseFactory, WinterStorageLeaseFactory
from payments.schema.types import BerthSwitchOfferNode, OrderNode
from payments.tests.factories import BerthSwitchOfferFactory, OrderFactory
from utils.relay import to_global_id

from ..enums import InvoicingType, OrganizationType
from ..schema import BoatCertificateNode, BoatNode, ProfileNode
from .factories import BoatFactory, OrganizationFactory

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
        "extend type ProfileNode  implements Node "
        ' @key(fields: "id") {   id: ID! @external '
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
            winterStorageApplications {
                edges {
                    node {
                        id
                    }
                }
            }
            winterStorageLeases {
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

    boat = BoatFactory(owner=customer_profile)
    berth_application = BerthApplicationFactory(customer=customer_profile, boat=boat)
    berth_lease = BerthLeaseFactory(customer=customer_profile, boat=boat)
    winter_storage_application = WinterStorageApplicationFactory(
        customer=customer_profile, boat=boat
    )
    winter_storage_lease = WinterStorageLeaseFactory(
        customer=customer_profile, boat=boat
    )
    organization = OrganizationFactory(customer=customer_profile)

    variables = {
        "_representations": [
            {"id": customer_profile_id, "__typename": ProfileNode._meta.name}
        ]
    }

    executed = api_client.execute(FEDERATED_PROFILES_QUERY, variables=variables)

    boat_id = to_global_id(BoatNode, boat.id)
    berth_application_id = to_global_id(BerthApplicationNode, berth_application.id)
    berth_lease_id = to_global_id(BerthLeaseNode, berth_lease.id)
    winter_storage_application_id = to_global_id(
        WinterStorageApplicationNode, winter_storage_application.id
    )
    winter_storage_lease_id = to_global_id(
        WinterStorageLeaseNode, winter_storage_lease.id
    )

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
        "winterStorageApplications": {
            "edges": [{"node": {"id": winter_storage_application_id}}]
        },
        "winterStorageLeases": {"edges": [{"node": {"id": winter_storage_lease_id}}]},
    }


FEDERATED_PROFILES_QUERY_WITH_ORDER_BY = """
query($_representations: [_Any!]!) {
    _entities(representations: $_representations) {
        ... on ProfileNode {
            id
            berthApplications(orderBy: "%s") {
                edges {
                    node {
                        id
                        createdAt
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
@pytest.mark.parametrize(
    "order_by,ascending", [("createdAt", True), ("-createdAt", False)]
)
def test_query_extended_profile_applications_order_by_created(
    order_by, ascending, api_client, customer_profile
):
    customer_profile_id = to_global_id(ProfileNode, customer_profile.id)

    with freeze_time("2020-02-01"):
        BerthApplicationFactory(customer=customer_profile)

    with freeze_time("2020-01-01"):
        BerthApplicationFactory(customer=customer_profile)

    variables = {
        "_representations": [
            {"id": customer_profile_id, "__typename": ProfileNode._meta.name}
        ]
    }

    query = FEDERATED_PROFILES_QUERY_WITH_ORDER_BY % order_by

    executed = api_client.execute(query, variables=variables)

    first_date = isoparse(
        executed["data"]["_entities"][0]["berthApplications"]["edges"][
            0 if ascending else 1
        ]["node"]["createdAt"]
    )
    second_date = isoparse(
        executed["data"]["_entities"][0]["berthApplications"]["edges"][
            1 if ascending else 0
        ]["node"]["createdAt"]
    )

    assert first_date < second_date


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
                winterStorageApplications {
                    edges {
                        node {
                            id
                        }
                    }
                }
                winterStorageLeases {
                    edges {
                        node {
                            id
                        }
                    }
                }
                orders {
                    edges {
                        node {
                            id
                        }
                    }
                }
                offers {
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
    boat = BoatFactory(owner=customer_profile)
    berth_application = BerthApplicationFactory(customer=customer_profile, boat=boat)
    berth_lease = BerthLeaseFactory(
        customer=customer_profile, boat=boat, status=LeaseStatus.PAID
    )
    winter_storage_application = WinterStorageApplicationFactory(
        customer=customer_profile, boat=boat
    )
    winter_storage_lease = WinterStorageLeaseFactory(
        customer=customer_profile, boat=boat
    )
    order = OrderFactory(lease=berth_lease, customer=customer_profile)
    offer = BerthSwitchOfferFactory(
        customer=customer_profile,
        lease=berth_lease,
        application__customer=customer_profile,
        application__boat=boat,
    )
    organization = OrganizationFactory(customer=customer_profile)

    executed = api_client.execute(QUERY_BERTH_PROFILES)

    customer_id = to_global_id(ProfileNode, customer_profile.id)
    boat_id = to_global_id(BoatNode, boat.id)
    berth_application_id = to_global_id(BerthApplicationNode, berth_application.id)
    offer_application_id = to_global_id(BerthApplicationNode, offer.application.id)
    berth_lease_id = to_global_id(BerthLeaseNode, berth_lease.id)
    winter_storage_application_id = to_global_id(
        WinterStorageApplicationNode, winter_storage_application.id
    )
    winter_storage_lease_id = to_global_id(
        WinterStorageLeaseNode, winter_storage_lease.id
    )
    order_id = to_global_id(OrderNode, order.id)
    offer_id = to_global_id(BerthSwitchOfferNode, offer.id)

    assert executed["data"]["berthProfiles"]["edges"][0]["node"] == {
        "id": customer_id,
        "invoicingType": customer_profile.invoicing_type.name,
        "comment": customer_profile.comment,
        "organization": {
            "businessId": organization.business_id,
            "name": organization.name,
        },
        "boats": {"edges": [{"node": {"id": boat_id}}]},
        "berthApplications": {
            "edges": [
                {"node": {"id": berth_application_id}},
                {"node": {"id": offer_application_id}},
            ]
        },
        "berthLeases": {"edges": [{"node": {"id": berth_lease_id}}]},
        "winterStorageApplications": {
            "edges": [{"node": {"id": winter_storage_application_id}}]
        },
        "winterStorageLeases": {"edges": [{"node": {"id": winter_storage_lease_id}}]},
        "orders": {"edges": [{"node": {"id": order_id}}]},
        "offers": {"edges": [{"node": {"id": offer_id}}]},
    }


@pytest.mark.parametrize(
    "api_client", ["api_client", "user", "harbor_services"], indirect=True
)
def test_query_berth_profiles_not_enough_permissions(api_client):
    executed = api_client.execute(QUERY_BERTH_PROFILES)

    assert_not_enough_permissions(executed)


QUERY_BERTH_PROFILES_FILTERED = """
query GetBerthProfilesByComment {
    berthProfiles(comment: "%s", invoicingTypes: [%s], customerGroups: [%s]) {
        edges {
            node {
                id
                comment
                invoicingType
                customerGroup
            }
        }
    }
}
"""


@pytest.mark.parametrize("should_find_match", [True, False])
def test_filter_berth_profiles_comment(
    should_find_match, superuser_api_client, customer_profile
):
    comment = "my lovely comment"
    customer_profile.comment = comment
    customer_profile.save()

    passed_comment = "totally different comment"
    if should_find_match:
        passed_comment = "lovely"

    query = QUERY_BERTH_PROFILES_FILTERED % (passed_comment, "", "")

    executed = superuser_api_client.execute(query)

    if should_find_match:
        assert (
            executed["data"]["berthProfiles"]["edges"][0]["node"]["comment"]
            == customer_profile.comment
        )
    else:
        assert not executed["data"]["berthProfiles"]["edges"]


@pytest.mark.parametrize("should_find_match", [True, False])
def test_filter_berth_profiles_invoicing_type(
    should_find_match, superuser_api_client, customer_profile
):
    customer_profile.invoicing_type = InvoicingType.ONLINE_PAYMENT
    customer_profile.save()

    passed_invoicing_type = InvoicingType.DIGITAL_INVOICE.name
    if should_find_match:
        passed_invoicing_type = customer_profile.invoicing_type.name

    query = QUERY_BERTH_PROFILES_FILTERED % ("", passed_invoicing_type, "")

    executed = superuser_api_client.execute(query)

    if should_find_match:
        assert (
            executed["data"]["berthProfiles"]["edges"][0]["node"]["invoicingType"]
            == passed_invoicing_type
        )
    else:
        assert not executed["data"]["berthProfiles"]["edges"]


@pytest.mark.parametrize("should_find_match", [True, False])
@pytest.mark.parametrize("organization_customer", [True, False])
def test_filter_berth_profiles_customer_group(
    should_find_match, organization_customer, superuser_api_client, customer_profile
):
    if organization_customer:
        organization = OrganizationFactory(
            customer=customer_profile, organization_type=OrganizationType.INTERNAL
        )

    passed_customer_group = OrganizationType.COMPANY.name
    if should_find_match:
        passed_customer_group = (
            organization.organization_type.name if organization_customer else "PRIVATE"
        )

    query = QUERY_BERTH_PROFILES_FILTERED % ("", "", passed_customer_group)

    executed = superuser_api_client.execute(query)

    if should_find_match:
        assert (
            executed["data"]["berthProfiles"]["edges"][0]["node"]["customerGroup"]
            == passed_customer_group
        )
    else:
        assert not executed["data"]["berthProfiles"]["edges"]


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
        winterStorageApplications {
            edges {
                node {
                    id
                }
            }
        }
        winterStorageLeases {
            edges {
                node {
                    id
                }
            }
        }
        orders {
            edges {
                node {
                    id
                }
            }
        }
        offers {
            edges {
                node {
                    id
                }
            }
        }
    }
}
"""


@pytest.mark.django_db
@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
def test_query_berth_profile(api_client, customer_profile):
    berth_profile_id = to_global_id(ProfileNode, customer_profile.id)

    boat = BoatFactory(owner=customer_profile)
    berth_application = BerthApplicationFactory(customer=customer_profile, boat=boat)
    berth_lease = BerthLeaseFactory(
        customer=customer_profile, boat=boat, status=LeaseStatus.PAID
    )
    winter_storage_application = WinterStorageApplicationFactory(
        customer=customer_profile, boat=boat
    )
    winter_storage_lease = WinterStorageLeaseFactory(
        customer=customer_profile, boat=boat
    )
    order = OrderFactory(
        lease=berth_lease,
    )
    offer = BerthSwitchOfferFactory(customer=customer_profile, lease=berth_lease)
    organization = OrganizationFactory(customer=customer_profile)

    query = QUERY_BERTH_PROFILE % berth_profile_id

    executed = api_client.execute(query)

    boat_id = to_global_id(BoatNode, boat.id)
    berth_application_id = to_global_id(BerthApplicationNode, berth_application.id)
    berth_lease_id = to_global_id(BerthLeaseNode, berth_lease.id)
    winter_storage_application_id = to_global_id(
        WinterStorageApplicationNode, winter_storage_application.id
    )
    winter_storage_lease_id = to_global_id(
        WinterStorageLeaseNode, winter_storage_lease.id
    )
    order_id = to_global_id(OrderNode, order.id)
    offer_id = to_global_id(BerthSwitchOfferNode, offer.id)

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
        "winterStorageApplications": {
            "edges": [{"node": {"id": winter_storage_application_id}}]
        },
        "winterStorageLeases": {"edges": [{"node": {"id": winter_storage_lease_id}}]},
        "orders": {"edges": [{"node": {"id": order_id}}]},
        "offers": {"edges": [{"node": {"id": offer_id}}]},
    }


def test_query_berth_profile_self_user(customer_profile):
    berth_profile_id = to_global_id(ProfileNode, customer_profile.id)

    boat = BoatFactory(owner=customer_profile)
    berth_application = BerthApplicationFactory(customer=customer_profile, boat=boat)
    berth_lease = BerthLeaseFactory(
        customer=customer_profile, boat=boat, status=LeaseStatus.PAID
    )
    winter_storage_application = WinterStorageApplicationFactory(
        customer=customer_profile, boat=boat
    )
    winter_storage_lease = WinterStorageLeaseFactory(
        customer=customer_profile, boat=boat
    )
    order = OrderFactory(lease=berth_lease)
    offer = BerthSwitchOfferFactory(customer=customer_profile, lease=berth_lease)
    organization = OrganizationFactory(customer=customer_profile)

    query = QUERY_BERTH_PROFILE % berth_profile_id

    api_client = create_api_client(user=customer_profile.user)
    executed = api_client.execute(query)

    boat_id = to_global_id(BoatNode, boat.id)
    berth_application_id = to_global_id(BerthApplicationNode, berth_application.id)
    berth_lease_id = to_global_id(BerthLeaseNode, berth_lease.id)
    winter_storage_application_id = to_global_id(
        WinterStorageApplicationNode, winter_storage_application.id
    )
    winter_storage_lease_id = to_global_id(
        WinterStorageLeaseNode, winter_storage_lease.id
    )
    order_id = to_global_id(OrderNode, order.id)
    offer_id = to_global_id(BerthSwitchOfferNode, offer.id)

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
        "winterStorageApplications": {
            "edges": [{"node": {"id": winter_storage_application_id}}]
        },
        "winterStorageLeases": {"edges": [{"node": {"id": winter_storage_lease_id}}]},
        "orders": {"edges": [{"node": {"id": order_id}}]},
        "offers": {"edges": [{"node": {"id": offer_id}}]},
    }


@pytest.mark.parametrize(
    "api_client",
    ["user", "harbor_services"],
    indirect=True,
)
def test_query_berth_profile_not_enough_permissions_valid_id(
    api_client, customer_profile
):
    berth_profile_id = to_global_id(ProfileNode, customer_profile.id)

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
    customer_id = to_global_id(ProfileNode, boat_certificate.boat.owner.id)

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


def test_query_customer_boat_count(superuser_api_client, customer_profile):
    count = random.randint(1, 10)
    for _i in range(count):
        BoatFactory(owner=customer_profile)

    query = """
        {
            berthProfile(id: "%s") {
                boats {
                    count
                    totalCount
                }
            }
        }
    """ % to_global_id(
        ProfileNode, customer_profile.id
    )

    executed = superuser_api_client.execute(query)
    assert executed["data"] == {
        "berthProfile": {"boats": {"count": count, "totalCount": count}}
    }


def test_query_berth_profile_count(superuser_api_client):
    count = random.randint(1, 10)
    for _i in range(count):
        CustomerProfileFactory()

    query = """
        {
            berthProfiles {
                count
                totalCount
            }
        }
    """

    executed = superuser_api_client.execute(query)
    assert executed["data"] == {"berthProfiles": {"count": count, "totalCount": count}}
