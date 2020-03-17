import pytest
from dateutil.parser import isoparse
from freezegun import freeze_time
from graphql_relay.node.node import to_global_id

from applications.enums import ApplicationStatus
from applications.tests.factories import BerthApplicationFactory
from berth_reservations.tests.utils import assert_in_errors
from leases.tests.factories import BerthLeaseFactory

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


def test_berth_applications_no_customer_filter_true(
    berth_application, superuser_api_client
):
    berth_application.customer = None
    berth_application.save()

    query = BERTH_APPLICATIONS_WITH_NO_CUSTOMER_FILTER_QUERY % "true"

    executed = superuser_api_client.execute(query)

    assert executed["data"] == {
        "berthApplications": {
            "edges": [
                {
                    "node": {
                        "id": to_global_id(
                            "BerthApplicationNode", berth_application.id
                        ),
                        "customer": None,
                    }
                }
            ]
        }
    }


def test_berth_applications_no_customer_filter_false(
    berth_application, superuser_api_client
):
    berth_application.customer = None
    berth_application.save()

    query = BERTH_APPLICATIONS_WITH_NO_CUSTOMER_FILTER_QUERY % "false"

    executed = superuser_api_client.execute(query)

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


def test_berth_applications_statuses_filter(berth_application, superuser_api_client):
    berth_application.lease = BerthLeaseFactory()
    berth_application.status = ApplicationStatus.HANDLED
    berth_application.save()

    status_enum_str = ApplicationStatus.HANDLED.name

    query = BERTH_APPLICATIONS_WITH_STATUSES_FILTER_QUERY % status_enum_str

    executed = superuser_api_client.execute(query)

    assert executed["data"] == {
        "berthApplications": {
            "edges": [
                {
                    "node": {
                        "id": to_global_id(
                            "BerthApplicationNode", berth_application.id
                        ),
                        "status": status_enum_str,
                    }
                }
            ]
        }
    }


def test_berth_applications_statuses_filter_empty(
    berth_application, superuser_api_client
):
    berth_application.lease = BerthLeaseFactory()
    berth_application.status = ApplicationStatus.HANDLED
    berth_application.save()

    status_enum_str = ApplicationStatus.PENDING.name

    query = BERTH_APPLICATIONS_WITH_STATUSES_FILTER_QUERY % status_enum_str

    executed = superuser_api_client.execute(query)

    assert executed["data"] == {"berthApplications": {"edges": []}}


def test_berth_applications_statuses_filter_invalid_enum(
    berth_application, superuser_api_client
):
    berth_application.lease = BerthLeaseFactory()
    berth_application.status = ApplicationStatus.HANDLED
    berth_application.save()

    nonexistent_enum_str = "FOOBAR"

    query = BERTH_APPLICATIONS_WITH_STATUSES_FILTER_QUERY % nonexistent_enum_str

    executed = superuser_api_client.execute(query)

    assert_in_errors(
        "invalid value [%s]." % nonexistent_enum_str, executed,
    )


def test_berth_applications_statuses_filter_empty_list(
    berth_application, superuser_api_client
):
    berth_application.lease = BerthLeaseFactory()
    berth_application.status = ApplicationStatus.HANDLED
    berth_application.save()

    empty_filter_str = ""

    query = BERTH_APPLICATIONS_WITH_STATUSES_FILTER_QUERY % empty_filter_str

    executed = superuser_api_client.execute(query)

    assert executed["data"] == {
        "berthApplications": {
            "edges": [
                {
                    "node": {
                        "id": to_global_id(
                            "BerthApplicationNode", berth_application.id
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
    "order_by,ascending", [("createdAt", True), ("-createdAt", False)]
)
def test_berth_applications_order_by_created(order_by, ascending, superuser_api_client):
    with freeze_time("2020-02-01"):
        BerthApplicationFactory()

    with freeze_time("2020-01-01"):
        BerthApplicationFactory()

    query = BERTH_APPLICATIONS_WITH_ORDER_BY % order_by

    executed = superuser_api_client.execute(query)

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


def test_berth_applications_order_by_created_at_default(superuser_api_client):
    with freeze_time("2020-02-01"):
        BerthApplicationFactory()

    with freeze_time("2020-01-01"):
        BerthApplicationFactory()

    executed = superuser_api_client.execute(BERTH_APPLICATIONS_QUERY)

    first_date = isoparse(
        executed["data"]["berthApplications"]["edges"][0]["node"]["createdAt"]
    )
    second_date = isoparse(
        executed["data"]["berthApplications"]["edges"][1]["node"]["createdAt"]
    )

    assert first_date < second_date
