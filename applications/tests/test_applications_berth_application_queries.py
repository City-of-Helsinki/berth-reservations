import random

import pytest
from dateutil.parser import isoparse
from freezegun import freeze_time
from graphql_relay.node.node import to_global_id

from berth_reservations.tests.utils import assert_in_errors, create_api_client
from customers.schema import ProfileNode
from leases.tests.factories import BerthLeaseFactory

from ..enums import ApplicationPriority, ApplicationStatus
from ..models import BerthApplication
from ..schema import BerthApplicationNode
from .factories import BerthApplicationFactory

BERTH_APPLICATIONS_WITH_NO_CUSTOMER_FILTER_QUERY = """
query APPLICATIONS {
    berthApplications(noCustomer: %s) {
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


@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
def test_berth_applications_no_customer_filter_true(berth_application, api_client):
    berth_application.customer = None
    berth_application.save()

    query = BERTH_APPLICATIONS_WITH_NO_CUSTOMER_FILTER_QUERY % "true"

    executed = api_client.execute(query)

    assert executed["data"] == {
        "berthApplications": {
            "edges": [
                {
                    "node": {
                        "id": to_global_id(
                            BerthApplicationNode._meta.name, berth_application.id
                        ),
                        "customer": None,
                    }
                }
            ]
        }
    }


@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
def test_berth_applications_no_customer_filter_false(berth_application, api_client):
    berth_application.customer = None
    berth_application.save()

    query = BERTH_APPLICATIONS_WITH_NO_CUSTOMER_FILTER_QUERY % "false"

    executed = api_client.execute(query)

    assert executed["data"] == {"berthApplications": {"edges": []}}


BERTH_APPLICATIONS_WITH_STATUSES_FILTER_QUERY = """
query APPLICATIONS {
    berthApplications(statuses: [%s]) {
        edges {
            node {
                id
                status
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
def test_berth_applications_statuses_filter(berth_application, api_client):
    berth_application.lease = BerthLeaseFactory()
    berth_application.status = ApplicationStatus.HANDLED
    berth_application.save()

    status_enum_str = ApplicationStatus.HANDLED.name

    query = BERTH_APPLICATIONS_WITH_STATUSES_FILTER_QUERY % status_enum_str

    executed = api_client.execute(query)

    assert executed["data"] == {
        "berthApplications": {
            "edges": [
                {
                    "node": {
                        "id": to_global_id(
                            BerthApplicationNode._meta.name, berth_application.id
                        ),
                        "status": status_enum_str,
                    }
                }
            ]
        }
    }


@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
def test_berth_applications_statuses_filter_empty(berth_application, api_client):
    berth_application.lease = BerthLeaseFactory()
    berth_application.status = ApplicationStatus.HANDLED
    berth_application.save()

    status_enum_str = ApplicationStatus.PENDING.name

    query = BERTH_APPLICATIONS_WITH_STATUSES_FILTER_QUERY % status_enum_str

    executed = api_client.execute(query)

    assert executed["data"] == {"berthApplications": {"edges": []}}


@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
def test_berth_applications_statuses_filter_invalid_enum(berth_application, api_client):
    berth_application.lease = BerthLeaseFactory()
    berth_application.status = ApplicationStatus.HANDLED
    berth_application.save()

    nonexistent_enum_str = "FOOBAR"

    query = BERTH_APPLICATIONS_WITH_STATUSES_FILTER_QUERY % nonexistent_enum_str

    executed = api_client.execute(query)

    assert_in_errors(
        "invalid value [%s]." % nonexistent_enum_str, executed,
    )


@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
def test_berth_applications_statuses_filter_empty_list(berth_application, api_client):
    berth_application.lease = BerthLeaseFactory()
    berth_application.status = ApplicationStatus.HANDLED
    berth_application.save()

    empty_filter_str = ""

    query = BERTH_APPLICATIONS_WITH_STATUSES_FILTER_QUERY % empty_filter_str

    executed = api_client.execute(query)

    assert executed["data"] == {
        "berthApplications": {
            "edges": [
                {
                    "node": {
                        "id": to_global_id(
                            BerthApplicationNode._meta.name, berth_application.id
                        ),
                        "status": ApplicationStatus.HANDLED.name,
                    }
                }
            ]
        }
    }


BERTH_APPLICATIONS_WITH_ORDER_BY = """
query APPLICATIONS {
    berthApplications(orderBy: "%s") {
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
@pytest.mark.parametrize(
    "order_by,ascending", [("createdAt", True), ("-createdAt", False)]
)
def test_berth_applications_order_by_created(order_by, ascending, api_client):
    with freeze_time("2020-02-01"):
        BerthApplicationFactory()

    with freeze_time("2020-01-01"):
        BerthApplicationFactory()

    query = BERTH_APPLICATIONS_WITH_ORDER_BY % order_by

    executed = api_client.execute(query)

    first_date = isoparse(
        executed["data"]["berthApplications"]["edges"][0 if ascending else 1]["node"][
            "createdAt"
        ]
    )
    second_date = isoparse(
        executed["data"]["berthApplications"]["edges"][1 if ascending else 0]["node"][
            "createdAt"
        ]
    )

    assert first_date < second_date


BERTH_APPLICATIONS_QUERY = """
query APPLICATIONS {
    berthApplications {
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
def test_berth_applications_order_by_created_at_default(api_client):
    with freeze_time("2020-02-01"):
        BerthApplicationFactory()

    with freeze_time("2020-01-01"):
        BerthApplicationFactory()

    executed = api_client.execute(BERTH_APPLICATIONS_QUERY)

    first_date = isoparse(
        executed["data"]["berthApplications"]["edges"][0]["node"]["createdAt"]
    )
    second_date = isoparse(
        executed["data"]["berthApplications"]["edges"][1]["node"]["createdAt"]
    )

    assert first_date < second_date


def test_query_berth_application_count(superuser_api_client):
    count = random.randint(1, 10)
    for _i in range(count):
        BerthApplicationFactory()

    query = """
        {
            berthApplications {
                count
                totalCount
            }
        }
    """

    executed = superuser_api_client.execute(query)
    assert executed["data"] == {
        "berthApplications": {"count": count, "totalCount": count}
    }


def test_query_berth_application_count_filtered(superuser_api_client, customer_profile):
    customer_count = random.randint(1, 10)
    no_customer_count = random.randint(1, 10)
    total_count = customer_count + no_customer_count

    for _i in range(customer_count):
        BerthApplicationFactory(customer=customer_profile)
    for _i in range(no_customer_count):
        BerthApplicationFactory(customer=None)

    query = """
        {
            berthApplications(noCustomer: %s) {
                count
                totalCount
            }
        }
    """

    executed = superuser_api_client.execute(query % "true")
    assert executed["data"] == {
        "berthApplications": {"count": no_customer_count, "totalCount": total_count}
    }

    executed = superuser_api_client.execute(query % "false")
    assert executed["data"] == {
        "berthApplications": {"count": customer_count, "totalCount": total_count}
    }


BERTH_APPLICATIONS_WITH_NAME_FILTER_QUERY = """
query APPLICATIONS {
    berthApplications(name: "%s") {
        edges {
            node {
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
@pytest.mark.parametrize(
    "name_filter", ["John", "Doe", "John Doe", "Doe John", "Do Joh", "hn oe"]
)
def test_berth_applications_name_filter(berth_application, api_client, name_filter):
    berth_application.first_name = "John"
    berth_application.last_name = "Doe"
    berth_application.save()

    query = BERTH_APPLICATIONS_WITH_NAME_FILTER_QUERY % name_filter
    executed = api_client.execute(query)

    assert executed["data"] == {
        "berthApplications": {
            "edges": [
                {
                    "node": {
                        "id": to_global_id(
                            BerthApplicationNode._meta.name, berth_application.id
                        ),
                    }
                }
            ]
        }
    }


@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
def test_berth_applications_name_filter_no_matching(berth_application, api_client):
    berth_application.first_name = "John"
    berth_application.last_name = "Doe"
    berth_application.save()

    query = BERTH_APPLICATIONS_WITH_NAME_FILTER_QUERY % "nomatches"
    executed = api_client.execute(query)

    assert executed["data"] == {"berthApplications": {"edges": []}}


BERTH_APPLICATIONS_WITH_APPLICATION_CODE_FILTER_QUERY = """
query APPLICATIONS {
    berthApplications(applicationCode: %s) {
        edges {
            node {
                applicationCode
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
def test_berth_applications_application_code_filter_true(
    berth_application, berth_application2, api_client
):
    berth_application.application_code = ""
    berth_application.save()

    berth_application2.application_code = "test"
    berth_application2.save()

    query = BERTH_APPLICATIONS_WITH_APPLICATION_CODE_FILTER_QUERY % "true"
    executed = api_client.execute(query)

    assert executed["data"] == {
        "berthApplications": {"edges": [{"node": {"applicationCode": "test"}}]}
    }


@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
def test_berth_applications_application_code_filter_false(
    berth_application, berth_application2, api_client
):
    berth_application.application_code = ""
    berth_application.save()

    berth_application2.application_code = "test"
    berth_application2.save()

    query = BERTH_APPLICATIONS_WITH_APPLICATION_CODE_FILTER_QUERY % "false"
    executed = api_client.execute(query)

    assert executed["data"] == {
        "berthApplications": {"edges": [{"node": {"applicationCode": ""}}]}
    }


BERTH_SWITCH_REASONS_QUERY = """
{
    berthSwitchReasons {
        id
        title
    }
}
"""


def test_get_berth_switch_reasons(superuser_api_client, berth_switch_reason):
    executed = superuser_api_client.execute(BERTH_SWITCH_REASONS_QUERY)
    assert executed == {
        "data": {
            "berthSwitchReasons": [
                {"id": str(berth_switch_reason.id), "title": berth_switch_reason.title}
            ]
        }
    }


CUSTOMER_OWN_BERTH_APPLICATIONS_QUERY = """
query APPLICATIONS {
    berthApplications {
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


def test_get_customer_own_berth_applications(customer_profile):
    customer_application = BerthApplicationFactory(customer=customer_profile)
    BerthApplicationFactory()

    api_client = create_api_client(user=customer_profile.user)
    executed = api_client.execute(CUSTOMER_OWN_BERTH_APPLICATIONS_QUERY)

    assert BerthApplication.objects.count() == 2

    assert len(executed["data"]["berthApplications"]["edges"]) == 1
    assert executed["data"]["berthApplications"]["edges"][0]["node"] == {
        "id": to_global_id(BerthApplicationNode._meta.name, customer_application.id),
        "customer": {"id": to_global_id(ProfileNode._meta.name, customer_profile.id)},
    }


BERTH_APPLICATION_PRIORITIES_QUERY = """
query APPLICATIONS {
    berthApplications {
        edges {
            node {
                createdAt
                priority
            }
        }
    }
}
"""


def test_berth_application_priority(superuser_api_client):
    # Because of "created_at", they should, be sorted from first-third, but with the
    # change on priorities, they're first sorted by priority
    with freeze_time("2020-01-01"):
        first_application = BerthApplicationFactory(priority=ApplicationPriority.LOW)

    with freeze_time("2020-02-01"):
        second_application = BerthApplicationFactory(
            priority=ApplicationPriority.MEDIUM
        )

    with freeze_time("2020-03-01"):
        third_application = BerthApplicationFactory(priority=ApplicationPriority.HIGH)

    executed = superuser_api_client.execute(BERTH_APPLICATION_PRIORITIES_QUERY)

    assert len(executed["data"]["berthApplications"]["edges"]) == 3

    assert executed["data"]["berthApplications"]["edges"][0]["node"] == {
        "createdAt": third_application.created_at.isoformat(),
        "priority": ApplicationPriority.HIGH.name,
    }

    assert executed["data"]["berthApplications"]["edges"][1]["node"] == {
        "createdAt": second_application.created_at.isoformat(),
        "priority": ApplicationPriority.MEDIUM.name,
    }

    assert executed["data"]["berthApplications"]["edges"][2]["node"] == {
        "createdAt": first_application.created_at.isoformat(),
        "priority": ApplicationPriority.LOW.name,
    }
