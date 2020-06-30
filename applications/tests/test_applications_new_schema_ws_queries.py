import random

import pytest
from dateutil.parser import isoparse
from freezegun import freeze_time
from graphql_relay.node.node import to_global_id

from applications.enums import ApplicationStatus
from applications.new_schema.types import WinterStorageApplicationNode
from applications.tests.factories import (
    WinterAreaChoiceFactory,
    WinterStorageApplicationFactory,
)
from berth_reservations.tests.utils import assert_in_errors

WS_APPLICATIONS_WITH_NO_CUSTOMER_FILTER_QUERY = """
query APPLICATIONS {
    winterStorageApplications(noCustomer: %s) {
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
def test_winter_storage_applications_no_customer_filter_true(
    winter_storage_application, api_client
):
    winter_storage_application.customer = None
    winter_storage_application.save()

    query = WS_APPLICATIONS_WITH_NO_CUSTOMER_FILTER_QUERY % "true"

    executed = api_client.execute(query)

    assert executed["data"] == {
        "winterStorageApplications": {
            "edges": [
                {
                    "node": {
                        "id": to_global_id(
                            WinterStorageApplicationNode._meta.name,
                            winter_storage_application.id,
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
def test_winter_storage_applications_no_customer_filter_false(
    winter_storage_application, api_client
):
    winter_storage_application.customer = None
    winter_storage_application.save()

    query = WS_APPLICATIONS_WITH_NO_CUSTOMER_FILTER_QUERY % "false"

    executed = api_client.execute(query)

    assert executed["data"] == {"winterStorageApplications": {"edges": []}}


WINTER_STORAGE_APPLICATIONS_WITH_STATUSES_FILTER_QUERY = """
query APPLICATIONS {
    winterStorageApplications(statuses: [%s]) {
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
def test_winter_storage_applications_statuses_filter(
    handled_ws_application, api_client
):

    status_enum_str = ApplicationStatus.HANDLED.name

    query = WINTER_STORAGE_APPLICATIONS_WITH_STATUSES_FILTER_QUERY % status_enum_str

    executed = api_client.execute(query)

    assert executed["data"] == {
        "winterStorageApplications": {
            "edges": [
                {
                    "node": {
                        "id": to_global_id(
                            WinterStorageApplicationNode._meta.name,
                            handled_ws_application.id,
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
def test_winter_storage_applications_statuses_filter_empty(
    handled_ws_application, api_client
):
    status_enum_str = ApplicationStatus.PENDING.name

    query = WINTER_STORAGE_APPLICATIONS_WITH_STATUSES_FILTER_QUERY % status_enum_str

    executed = api_client.execute(query)

    assert executed["data"] == {"winterStorageApplications": {"edges": []}}


def test_winter_storage_applications_statuses_filter_invalid_enum(
    handled_ws_application, superuser_api_client
):
    nonexistent_enum_str = "FOOBAR"

    query = (
        WINTER_STORAGE_APPLICATIONS_WITH_STATUSES_FILTER_QUERY % nonexistent_enum_str
    )

    executed = superuser_api_client.execute(query)

    assert_in_errors(
        "invalid value [%s]." % nonexistent_enum_str, executed,
    )


def test_winter_storage_applications_statuses_filter_empty_list(
    handled_ws_application, superuser_api_client
):

    empty_filter_str = ""

    query = WINTER_STORAGE_APPLICATIONS_WITH_STATUSES_FILTER_QUERY % empty_filter_str

    executed = superuser_api_client.execute(query)

    assert executed["data"] == {
        "winterStorageApplications": {
            "edges": [
                {
                    "node": {
                        "id": to_global_id(
                            WinterStorageApplicationNode._meta.name,
                            handled_ws_application.id,
                        ),
                        "status": ApplicationStatus.HANDLED.name,
                    }
                }
            ]
        }
    }


WINTER_STORAGE_APPLICATIONS_WITH_ORDER_BY = """
query APPLICATIONS {
    winterStorageApplications(orderBy: "%s") {
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
def test_winter_storage_applications_order_by_created(
    order_by, ascending, superuser_api_client
):
    with freeze_time("2020-02-01"):
        WinterStorageApplicationFactory()

    with freeze_time("2020-01-01"):
        WinterStorageApplicationFactory()

    query = WINTER_STORAGE_APPLICATIONS_WITH_ORDER_BY % order_by

    executed = superuser_api_client.execute(query)

    first_date = isoparse(
        executed["data"]["winterStorageApplications"]["edges"][0 if ascending else 1][
            "node"
        ]["createdAt"]
    )
    second_date = isoparse(
        executed["data"]["winterStorageApplications"]["edges"][1 if ascending else 0][
            "node"
        ]["createdAt"]
    )

    assert first_date < second_date


WINTER_STORAGE_APPLICATIONS_QUERY = """
query APPLICATIONS {
    winterStorageApplications {
        edges {
            node {
                createdAt
            }
        }
    }
}
"""


def test_winter_storage_applications_order_by_created_at_default(superuser_api_client):
    with freeze_time("2020-02-01"):
        WinterStorageApplicationFactory()

    with freeze_time("2020-01-01"):
        WinterStorageApplicationFactory()

    executed = superuser_api_client.execute(WINTER_STORAGE_APPLICATIONS_QUERY)

    first_date = isoparse(
        executed["data"]["winterStorageApplications"]["edges"][0]["node"]["createdAt"]
    )
    second_date = isoparse(
        executed["data"]["winterStorageApplications"]["edges"][1]["node"]["createdAt"]
    )

    assert first_date < second_date


def test_query_winter_storage_application_count(superuser_api_client):
    count = random.randint(1, 10)
    for _i in range(count):
        WinterStorageApplicationFactory()

    query = """
        {
            winterStorageApplications {
                count
                totalCount
            }
        }
    """

    executed = superuser_api_client.execute(query)
    assert executed["data"] == {
        "winterStorageApplications": {"count": count, "totalCount": count}
    }


def test_query_winter_storage_application_count_filtered(
    superuser_api_client, customer_profile
):
    customer_count = random.randint(1, 10)
    no_customer_count = random.randint(1, 10)
    total_count = customer_count + no_customer_count

    for _i in range(customer_count):
        WinterStorageApplicationFactory(customer=customer_profile)
    for _i in range(no_customer_count):
        WinterStorageApplicationFactory(customer=None)

    query = """
        {
            winterStorageApplications(noCustomer: %s) {
                count
                totalCount
            }
        }
    """

    executed = superuser_api_client.execute(query % "true")
    assert executed["data"] == {
        "winterStorageApplications": {
            "count": no_customer_count,
            "totalCount": total_count,
        }
    }

    executed = superuser_api_client.execute(query % "false")
    assert executed["data"] == {
        "winterStorageApplications": {
            "count": customer_count,
            "totalCount": total_count,
        }
    }


WINTER_STORAGE_APPLICATION_QUERY = """
query APPLICATION {
    winterStorageApplication(id: "%s") {
        id
        boatType
        winterStorageAreaChoices {
            winterStorageAreaName
            priority
        }
        customer {
            id
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_services", "berth_handler", "berth_supervisor"],
    indirect=True,
)
def test_winter_storage_application_query(winter_storage_application, api_client):
    WinterAreaChoiceFactory(priority=2, application=winter_storage_application)
    WinterAreaChoiceFactory(priority=1, application=winter_storage_application)

    application_id = to_global_id(
        WinterStorageApplicationNode._meta.name, winter_storage_application.id,
    )

    query = WINTER_STORAGE_APPLICATION_QUERY % application_id

    executed = api_client.execute(query)

    application = executed["data"]["winterStorageApplication"]
    assert application["id"] == application_id
    assert application["customer"] is None
    assert len(application["boatType"]) > 0

    areas = application["winterStorageAreaChoices"]
    assert len(areas) == 2

    first_area = areas[0]
    assert first_area["priority"] == 1
    assert len(first_area["winterStorageAreaName"]) > 0

    second_area = areas[1]
    assert second_area["priority"] == 2
    assert len(second_area["winterStorageAreaName"]) > 0
