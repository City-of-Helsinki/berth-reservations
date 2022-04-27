import itertools
import random
from datetime import date
from unittest.mock import patch

import pytest
from dateutil.parser import isoparse
from freezegun import freeze_time

from applications.enums import ApplicationAreaType
from applications.schema import BerthApplicationNode, WinterStorageApplicationNode
from applications.tests.factories import (
    BerthApplicationFactory,
    WinterStorageApplicationFactory,
)
from berth_reservations.tests.factories import CustomerProfileFactory, UserFactory
from berth_reservations.tests.utils import (
    assert_in_errors,
    assert_not_enough_permissions,
    create_api_client,
)
from leases.enums import LeaseStatus
from leases.schema import BerthLeaseNode, WinterStorageLeaseNode
from leases.tests.factories import BerthLeaseFactory, WinterStorageLeaseFactory
from payments.schema.types import BerthSwitchOfferNode, OrderNode
from payments.tests.factories import BerthSwitchOfferFactory, OrderFactory
from resources.schema import (
    BerthNode,
    HarborNode,
    PierNode,
    WinterStorageAreaNode,
    WinterStoragePlaceNode,
)
from resources.tests.factories import (
    BerthFactory,
    BoatTypeFactory,
    HarborFactory,
    PierFactory,
    WinterStorageAreaFactory,
    WinterStoragePlaceFactory,
    WinterStorageSectionFactory,
)
from utils.relay import to_global_id

from ..enums import InvoicingType, OrganizationType
from ..schema import BoatCertificateNode, BoatNode, ProfileNode
from ..services import HelsinkiProfileUser
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

    passed_invoicing_type = InvoicingType.PAPER_INVOICE.name
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


def test_filter_profile_by_customer_groups(superuser_api_client):
    company_profile = CustomerProfileFactory()
    OrganizationFactory(
        customer=company_profile, organization_type=OrganizationType.INTERNAL
    )
    internal_profile = CustomerProfileFactory()
    OrganizationFactory(
        customer=internal_profile, organization_type=OrganizationType.INTERNAL
    )
    private_profile = (
        CustomerProfileFactory()
    )  # Private customer profile, just to add noise to the filter
    query = (
        """
    {
            berthProfiles(customerGroups: [%s]) {
                edges{
                    node{
                       id
                    }
                }
            }
    }
    """
        % "PRIVATE"
    )
    executed = superuser_api_client.execute(query)
    assert to_global_id(ProfileNode, private_profile.id) in str(executed["data"])
    assert to_global_id(ProfileNode, company_profile.id) not in str(executed["data"])
    assert to_global_id(ProfileNode, internal_profile.id) not in str(executed["data"])

    query = """
    {
            berthProfiles(customerGroups: [%s, %s]) {
                edges{
                    node{
                       id
                    }
                }
            }
    }
    """ % (
        OrganizationType.INTERNAL.upper(),
        OrganizationType.COMPANY.upper(),
    )
    executed = superuser_api_client.execute(query)
    assert to_global_id(ProfileNode, private_profile.id) not in str(executed["data"])
    assert to_global_id(ProfileNode, company_profile.id) in str(executed["data"])
    assert to_global_id(ProfileNode, internal_profile.id) in str(executed["data"])


def test_filter_profile_by_lease_statuses(superuser_api_client):
    offered_lease = BerthLeaseFactory(status=LeaseStatus.OFFERED)
    refused_lease = WinterStorageLeaseFactory(status=LeaseStatus.REFUSED)
    paid_lease = BerthLeaseFactory(status=LeaseStatus.PAID)

    query = """
    {
            berthProfiles(leaseStatuses: [%s, %s]) {
                edges{
                    node{
                       id
                    }
                }
            }
    }
    """ % (
        LeaseStatus.OFFERED.upper(),
        LeaseStatus.REFUSED.upper(),
    )

    executed = superuser_api_client.execute(query)
    assert to_global_id(ProfileNode, offered_lease.customer.id) in str(executed["data"])
    assert to_global_id(ProfileNode, refused_lease.customer.id) in str(executed["data"])
    assert to_global_id(ProfileNode, paid_lease.customer.id) not in str(
        executed["data"]
    )


def test_filter_profile_by_lease_start(superuser_api_client):
    lease_1 = BerthLeaseFactory(
        start_date=date(day=15, month=9, year=2020),
        end_date=date(day=15, month=10, year=2020),
    )
    lease_2 = WinterStorageLeaseFactory(
        start_date=date(day=15, month=9, year=2020),
        end_date=date(day=15, month=10, year=2020),
    )
    lease_3 = BerthLeaseFactory(
        start_date=date(day=10, month=9, year=2020),
        end_date=date(day=10, month=10, year=2020),
    )

    query = (
        """
    {
            berthProfiles(leaseStart: "%s") {
                edges{
                    node{
                       id
                    }
                }
            }
    }
    """
        % "2020-09-14"
    )

    executed = superuser_api_client.execute(query)
    assert to_global_id(ProfileNode, lease_1.customer.id) in str(executed["data"])
    assert to_global_id(ProfileNode, lease_2.customer.id) in str(executed["data"])
    assert to_global_id(ProfileNode, lease_3.customer.id) not in str(executed["data"])


def test_filter_profile_by_lease_end(superuser_api_client):
    lease_1 = BerthLeaseFactory(
        start_date=date(day=15, month=9, year=2020),
        end_date=date(day=15, month=10, year=2020),
    )
    lease_2 = WinterStorageLeaseFactory(
        start_date=date(day=15, month=9, year=2020),
        end_date=date(day=15, month=10, year=2020),
    )
    lease_3 = BerthLeaseFactory(
        start_date=date(day=10, month=9, year=2020),
        end_date=date(day=20, month=10, year=2020),
    )

    query = (
        """
    {
            berthProfiles(leaseEnd: "%s") {
                edges{
                    node{
                       id
                    }
                }
            }
    }
    """
        % "2020-10-18"
    )

    executed = superuser_api_client.execute(query)
    assert to_global_id(ProfileNode, lease_1.customer.id) in str(executed["data"])
    assert to_global_id(ProfileNode, lease_2.customer.id) in str(executed["data"])
    assert to_global_id(ProfileNode, lease_3.customer.id) not in str(executed["data"])


@pytest.mark.parametrize(
    "lease_amount,winter_storage_amount", itertools.product((0, 1, 2), repeat=2)
)
def test_filter_profile_by_berth_count(
    superuser_api_client, lease_amount: int, winter_storage_amount: int
):
    profile = CustomerProfileFactory()

    for _i in range(lease_amount):
        BerthLeaseFactory(customer=profile)
    for _i in range(winter_storage_amount):
        WinterStorageLeaseFactory(customer=profile)

    query = """
    {
            berthProfiles(leaseCount: true) {
                edges{
                    node{
                       id
                    }
                }
            }
    }
    """
    executed = superuser_api_client.execute(query)

    if lease_amount > 1 or winter_storage_amount > 1:
        assert to_global_id(ProfileNode, profile.id) in str(executed["data"])
    else:
        assert to_global_id(ProfileNode, profile.id) not in str(executed["data"])


def test_filter_profile_by_boat_types(superuser_api_client):
    boat_type_1 = BoatTypeFactory()
    boat_type_2 = BoatTypeFactory()
    boat_type_3 = BoatTypeFactory()
    BoatTypeFactory()
    boat_1 = BoatFactory(boat_type=boat_type_1)
    boat_2 = BoatFactory(boat_type=boat_type_2)
    boat_3 = BoatFactory(boat_type=boat_type_3)
    query = """
    {
            berthProfiles(boatTypes: [ %d, %d]) {
                edges{
                    node{
                       id
                    }
                }
            }
    }
    """ % (
        boat_type_1.id,
        boat_type_2.id,
    )
    executed = superuser_api_client.execute(query)
    assert to_global_id(ProfileNode, boat_1.owner.id) in str(executed["data"])
    assert to_global_id(ProfileNode, boat_2.owner.id) in str(executed["data"])
    assert to_global_id(ProfileNode, boat_3.owner.id) not in str(executed["data"])


def test_filter_profile_by_boat_registration_number(superuser_api_client):
    boat_1 = BoatFactory()
    boat_2 = BoatFactory()
    assert boat_1.registration_number != boat_2.registration_number
    query = (
        """
    {
            berthProfiles(boatRegistrationNumber: "%s") {
                edges{
                    node{
                       id
                    }
                }
            }
    }
    """
        % boat_1.registration_number
    )
    executed = superuser_api_client.execute(query)
    assert to_global_id(ProfileNode, boat_1.owner.id) in str(executed["data"])
    assert to_global_id(ProfileNode, boat_2.owner.id) not in str(executed["data"])


def test_filter_profile_by_harbors(superuser_api_client):
    harbor_1 = HarborFactory()
    harbor_2 = HarborFactory()
    harbor_3 = HarborFactory()
    profile_1 = BerthLeaseFactory(
        berth=BerthFactory(pier=PierFactory(harbor=harbor_1))
    ).customer
    profile_2 = BerthLeaseFactory(
        berth=BerthFactory(pier=PierFactory(harbor=harbor_2))
    ).customer
    profile_3 = BerthLeaseFactory(
        berth=BerthFactory(pier=PierFactory(harbor=harbor_3))
    ).customer
    query = """
        {
                berthProfiles(harbors: ["%s", "%s"]) {
                    edges{
                        node{
                           id
                        }
                    }
                }
        }
    """ % (
        to_global_id(HarborNode, harbor_1.id),
        to_global_id(HarborNode, harbor_2.id),
    )
    executed = superuser_api_client.execute(query)
    assert to_global_id(ProfileNode, profile_1.id) in str(executed["data"])
    assert to_global_id(ProfileNode, profile_2.id) in str(executed["data"])
    assert to_global_id(ProfileNode, profile_3.id) not in str(executed["data"])


def test_filter_profile_by_piers(superuser_api_client):
    pier_1 = PierFactory()
    pier_2 = PierFactory()
    pier_3 = PierFactory()
    profile_1 = BerthLeaseFactory(berth=BerthFactory(pier=pier_1)).customer
    profile_2 = BerthLeaseFactory(berth=BerthFactory(pier=pier_2)).customer
    profile_3 = BerthLeaseFactory(berth=BerthFactory(pier=pier_3)).customer
    query = """
            {
                    berthProfiles(piers: ["%s", "%s"]) {
                        edges{
                            node{
                               id
                            }
                        }
                    }
            }
        """ % (
        to_global_id(PierNode, pier_1.id),
        to_global_id(PierNode, pier_2.id),
    )
    executed = superuser_api_client.execute(query)
    assert to_global_id(ProfileNode, profile_1.id) in str(executed["data"])
    assert to_global_id(ProfileNode, profile_2.id) in str(executed["data"])
    assert to_global_id(ProfileNode, profile_3.id) not in str(executed["data"])


def test_filter_profile_by_berth(superuser_api_client):
    berth_1 = BerthFactory()
    berth_2 = BerthFactory()
    berth_3 = BerthFactory()
    profile_1 = BerthLeaseFactory(berth=berth_1).customer
    profile_2 = BerthLeaseFactory(berth=berth_2).customer
    profile_3 = BerthLeaseFactory(berth=berth_3).customer
    query = """
        {
                berthProfiles(berths: ["%s", "%s"]) {
                    edges{
                        node{
                           id
                        }
                    }
                }
        }
    """ % (
        to_global_id(BerthNode, berth_1.id),
        to_global_id(BerthNode, berth_2.id),
    )
    executed = superuser_api_client.execute(query)
    assert to_global_id(ProfileNode, profile_1.id) in str(executed["data"])
    assert to_global_id(ProfileNode, profile_2.id) in str(executed["data"])
    assert to_global_id(ProfileNode, profile_3.id) not in str(executed["data"])


def test_filter_profile_by_marked_ws_areas(superuser_api_client):
    ws_area_1 = WinterStorageAreaFactory()
    ws_area_2 = WinterStorageAreaFactory()
    ws_area_3 = WinterStorageAreaFactory()
    profile_1 = WinterStorageLeaseFactory(
        application=WinterStorageApplicationFactory(
            area_type=ApplicationAreaType.MARKED
        ),
        place=WinterStoragePlaceFactory(
            winter_storage_section=WinterStorageSectionFactory(area=ws_area_1)
        ),
    ).customer
    profile_2 = WinterStorageLeaseFactory(
        application=WinterStorageApplicationFactory(
            area_type=ApplicationAreaType.MARKED
        ),
        place=None,
        section=WinterStorageSectionFactory(area=ws_area_2),
    ).customer
    profile_3 = WinterStorageLeaseFactory(
        application=WinterStorageApplicationFactory(
            area_type=ApplicationAreaType.MARKED
        ),
        place=WinterStoragePlaceFactory(
            winter_storage_section=WinterStorageSectionFactory(area=ws_area_3)
        ),
    ).customer
    query = """
        {
                berthProfiles(markedWinterStorageAreas: ["%s", "%s"]) {
                    edges{
                        node{
                           id
                        }
                    }
                }
        }
    """ % (
        to_global_id(WinterStorageAreaNode, ws_area_1.id),
        to_global_id(WinterStorageAreaNode, ws_area_2.id),
    )
    executed = superuser_api_client.execute(query)
    assert to_global_id(ProfileNode, profile_1.id) in str(executed["data"])
    assert to_global_id(ProfileNode, profile_2.id) in str(executed["data"])
    assert to_global_id(ProfileNode, profile_3.id) not in str(executed["data"])


def test_filter_profile_by_marked_ws_places(superuser_api_client):
    ws_place_1 = WinterStoragePlaceFactory()
    ws_place_2 = WinterStoragePlaceFactory()
    ws_place_3 = WinterStoragePlaceFactory()
    profile_1 = WinterStorageLeaseFactory(
        application=WinterStorageApplicationFactory(
            area_type=ApplicationAreaType.MARKED
        ),
        place=ws_place_1,
    ).customer
    profile_2 = WinterStorageLeaseFactory(
        application=WinterStorageApplicationFactory(
            area_type=ApplicationAreaType.MARKED
        ),
        place=ws_place_2,
    ).customer
    profile_3 = WinterStorageLeaseFactory(
        application=WinterStorageApplicationFactory(
            area_type=ApplicationAreaType.MARKED
        ),
        place=ws_place_3,
    ).customer
    query = """
           {
                   berthProfiles(markedWinterStoragePlaces: ["%s", "%s"]) {
                       edges{
                           node{
                              id
                           }
                       }
                   }
           }
       """ % (
        to_global_id(WinterStoragePlaceNode, ws_place_1.id),
        to_global_id(WinterStoragePlaceNode, ws_place_2.id),
    )
    executed = superuser_api_client.execute(query)
    assert to_global_id(ProfileNode, profile_1.id) in str(executed["data"])
    assert to_global_id(ProfileNode, profile_2.id) in str(executed["data"])
    assert to_global_id(ProfileNode, profile_3.id) not in str(executed["data"])


def test_filter_profile_by_unmarked_ws_areas(superuser_api_client):
    ws_area_1 = WinterStorageAreaFactory()
    ws_area_2 = WinterStorageAreaFactory()
    ws_area_3 = WinterStorageAreaFactory()
    profile_1 = WinterStorageLeaseFactory(
        application=WinterStorageApplicationFactory(
            area_type=ApplicationAreaType.UNMARKED
        ),
        place=WinterStoragePlaceFactory(
            winter_storage_section=WinterStorageSectionFactory(area=ws_area_1)
        ),
    ).customer
    profile_2 = WinterStorageLeaseFactory(
        application=WinterStorageApplicationFactory(
            area_type=ApplicationAreaType.UNMARKED
        ),
        place=None,
        section=WinterStorageSectionFactory(area=ws_area_2),
    ).customer
    profile_3 = WinterStorageLeaseFactory(
        application=WinterStorageApplicationFactory(
            area_type=ApplicationAreaType.UNMARKED
        ),
        place=WinterStoragePlaceFactory(
            winter_storage_section=WinterStorageSectionFactory(area=ws_area_3)
        ),
    ).customer
    query = """
            {
                    berthProfiles(unmarkedWinterStorageAreas: ["%s", "%s"]) {
                        edges{
                            node{
                               id
                            }
                        }
                    }
            }
        """ % (
        to_global_id(WinterStorageAreaNode, ws_area_1.id),
        to_global_id(WinterStorageAreaNode, ws_area_2.id),
    )
    executed = superuser_api_client.execute(query)
    assert to_global_id(ProfileNode, profile_1.id) in str(executed["data"])
    assert to_global_id(ProfileNode, profile_2.id) in str(executed["data"])
    assert to_global_id(ProfileNode, profile_3.id) not in str(executed["data"])


def test_filter_profile_by_sticker_number(superuser_api_client):
    profile_1 = WinterStorageLeaseFactory(
        application=WinterStorageApplicationFactory(
            area_type=ApplicationAreaType.UNMARKED
        ),
        sticker_number="1",
    ).customer
    profile_2 = WinterStorageLeaseFactory(
        application=WinterStorageApplicationFactory(
            area_type=ApplicationAreaType.UNMARKED
        ),
        sticker_number="2",
    ).customer
    query = (
        """
    {
            berthProfiles(stickerNumber: "%s") {
                edges{
                    node{
                       id
                    }
                }
            }
    }
    """
        % "1"
    )
    executed = superuser_api_client.execute(query)
    assert to_global_id(ProfileNode, profile_1.id) in str(executed["data"])
    assert to_global_id(ProfileNode, profile_2.id) not in str(executed["data"])


def test_filter_by_hki_profile_filters_without_profile_token(superuser_api_client):
    CustomerProfileFactory()  # needed to trigger the profile query, or otherwise no ids
    query = """
        {
                berthProfiles(email: "example@email.com") {
                    edges{
                        node{
                           id
                        }
                    }
                }
        }
    """
    executed = superuser_api_client.execute(query)
    assert_in_errors("API Token", executed)


@patch("customers.services.profile.ProfileService.find_profile")
def test_filter_by_hki_profile_filters(mock_find_profile, superuser_api_client):
    profile_1 = WinterStorageLeaseFactory(
        application=WinterStorageApplicationFactory(
            area_type=ApplicationAreaType.UNMARKED
        ),
        sticker_number="1",
    ).customer
    profile_2 = CustomerProfileFactory()
    profile_3 = CustomerProfileFactory()
    mock_find_profile.return_value = [
        HelsinkiProfileUser(
            profile_1.id,
            email=profile_1.user.email,
            first_name=profile_1.user.first_name,
            last_name="Last Name",
        ),
        HelsinkiProfileUser(
            profile_2.id,
            email=profile_2.user.email,
            first_name=profile_2.user.first_name,
            last_name="Last Name",
        ),
        HelsinkiProfileUser(
            profile_3.id,
            email=profile_3.user.email,
            first_name=profile_3.user.first_name,
            last_name="Last Name",
        ),
    ]
    # First query should return all mock profiles
    query = """
        {
                berthProfiles(lastName: "Last Name", apiToken: "Sample token") {
                    edges{
                        node{
                           id
                        }
                    }
                }
        }
    """

    executed = superuser_api_client.execute(query)
    assert len(executed["data"]["berthProfiles"]["edges"]) == 3
    assert to_global_id(ProfileNode, profile_1.id) in str(executed["data"])
    assert to_global_id(ProfileNode, profile_2.id) in str(executed["data"])
    assert to_global_id(ProfileNode, profile_3.id) in str(executed["data"])
    # Second query will filter profiles by Berth Profile fields
    query = """
            {
                    berthProfiles(lastName: "Last Name", apiToken: "Sample token", stickerNumber: "1") {
                        edges{
                            node{
                               id
                            }
                        }
                    }
            }
        """
    mock_find_profile.return_value = [
        HelsinkiProfileUser(
            profile_1.id,
            email=profile_1.user.email,
            first_name=profile_1.user.first_name,
            last_name="Last Name",
        ),
    ]
    executed = superuser_api_client.execute(query)
    mock_find_profile.assert_called_with(
        first_name="",
        last_name="Last Name",
        email="",
        address="",
        order_by="",
        first=100,
        ids=[str(profile_1.id)],
        force_only_one=False,
        recursively_fetch_all=True,
        ids_only=True,
    )
    assert to_global_id(ProfileNode, profile_1.id) in str(executed["data"])
    assert to_global_id(ProfileNode, profile_2.id) not in str(executed["data"])
    assert to_global_id(ProfileNode, profile_3.id) not in str(executed["data"])


@patch("customers.services.profile.ProfileService.find_profile")
@pytest.mark.parametrize(
    "names",
    [
        ["A", "B", "C", "D", "E", "F"],
        ["D", "E", "F", "C", "B", "A"],
        ["X", "X", "A", "X", "B", "C"],
    ],
)
def test_filter_by_hki_profile_order_by(mock_find_profile, names, superuser_api_client):
    profiles = [
        CustomerProfileFactory(user=UserFactory(first_name=name, last_name=name))
        for name in names
    ]
    mock_find_profile.return_value = [
        HelsinkiProfileUser(
            profile.id,
            email=profile.user.email,
            first_name=profile.user.first_name,
            last_name="Last name",
        )
        for profile in profiles
    ]

    query = """
            {
                    berthProfiles(lastName: "Last Name", apiToken: "Sample token") {
                        edges{
                            node{
                               id
                            }
                        }
                    }
            }
        """
    executed = superuser_api_client.execute(query)
    # The results set should be ordered in the same order as mocked profiles
    assert [to_global_id(ProfileNode, profile.id) for profile in profiles] == [
        node["id"]
        for node in [
            edge["node"] for edge in executed["data"]["berthProfiles"]["edges"]
        ]
    ]
