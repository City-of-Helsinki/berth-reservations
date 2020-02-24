from graphql_relay.node.node import to_global_id

from berth_reservations.tests.utils import GraphQLTestClient

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
