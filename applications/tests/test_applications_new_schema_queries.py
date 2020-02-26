from graphql_relay.node.node import to_global_id

from applications.enums import ApplicationStatus
from berth_reservations.tests.utils import assert_in_errors, GraphQLTestClient

GRAPHQL_URL = "/graphql_v2/"


def test_berth_applications_no_customer_filter_true(berth_application, superuser):
    berth_application.customer = None
    berth_application.save()

    client = GraphQLTestClient()
    query = """
        query APPLICATIONS {
            berthApplications(noCustomer: true) {
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
    executed = client.execute(query=query, graphql_url=GRAPHQL_URL, user=superuser)

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


def test_berth_applications_no_customer_filter_false(berth_application, superuser):
    berth_application.customer = None
    berth_application.save()

    client = GraphQLTestClient()
    query = """
        query APPLICATIONS {
            berthApplications(noCustomer: false) {
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
    executed = client.execute(query=query, graphql_url=GRAPHQL_URL, user=superuser)

    assert executed["data"] == {"berthApplications": {"edges": []}}


def test_berth_applications_statuses_filter(berth_application, superuser):
    berth_application.status = ApplicationStatus.HANDLED
    berth_application.save()

    client = GraphQLTestClient()
    query = """
        query APPLICATIONS {
            berthApplications(statuses: [HANDLED]) {
                edges {
                    node {
                        id
                        status
                    }
                }
            }
        }
    """
    executed = client.execute(query=query, graphql_url=GRAPHQL_URL, user=superuser)

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


def test_berth_applications_statuses_filter_empty(berth_application, superuser):
    berth_application.status = ApplicationStatus.HANDLED
    berth_application.save()

    client = GraphQLTestClient()
    query = """
        query APPLICATIONS {
            berthApplications(statuses: [PENDING]) {
                edges {
                    node {
                        id
                        status
                    }
                }
            }
        }
    """
    executed = client.execute(query=query, graphql_url=GRAPHQL_URL, user=superuser)

    assert executed["data"] == {"berthApplications": {"edges": []}}


def test_berth_applications_statuses_filter_invalid_enum(berth_application, superuser):
    berth_application.status = ApplicationStatus.HANDLED
    berth_application.save()

    client = GraphQLTestClient()
    query = """
        query APPLICATIONS {
            berthApplications(statuses: [FOOBAR]) {
                edges {
                    node {
                        id
                        status
                    }
                }
            }
        }
    """
    executed = client.execute(query=query, graphql_url=GRAPHQL_URL, user=superuser)
    assert_in_errors(
        "invalid value [FOOBAR].", executed,
    )


def test_berth_applications_statuses_filter_empty_list(berth_application, superuser):
    berth_application.status = ApplicationStatus.HANDLED
    berth_application.save()

    client = GraphQLTestClient()
    query = """
        query APPLICATIONS {
            berthApplications(statuses: []) {
                edges {
                    node {
                        id
                        status
                    }
                }
            }
        }
    """
    executed = client.execute(query=query, graphql_url=GRAPHQL_URL, user=superuser)

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
