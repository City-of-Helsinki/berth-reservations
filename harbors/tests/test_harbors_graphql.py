from berth_reservations.tests.utils import GraphQLTestClient


def test_get_boat_type(boat_type):
    client = GraphQLTestClient()
    query = """
        {
            boatTypes {
                name
            }
        }
    """
    executed = client.execute(query)
    assert executed == {"data": {"boatTypes": [{"name": "Dinghy"}]}}


def test_get_harbors(harbor):
    client = GraphQLTestClient()
    query = """
        {
            harbors {
                edges {
                    node {
                        properties {
                            name
                            zipCode
                        }
                    }
                }
            }
        }
    """
    executed = client.execute(query)
    assert executed == {
        "data": {
            "harbors": {
                "edges": [
                    {
                        "node": {
                            "properties": {"name": "Sunny Harbor", "zipCode": "00100"}
                        }
                    }
                ]
            }
        }
    }
