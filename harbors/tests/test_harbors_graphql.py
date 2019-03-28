from graphene.test import Client

from berth_reservations.schema import schema


def test_get_boat_type(boat_type):
    client = Client(schema)
    query = """
        {
            boatTypes{
                identifier
            }
        }
    """
    executed = client.execute(query)
    assert executed == {"data": {"boatTypes": [{"identifier": "dinghy"}]}}


def test_get_harbors(harbor):
    client = Client(schema)
    query = """
        {
            harbors{
                edges{
                node{
                            properties{
                    identifier
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
                            "properties": {
                                "identifier": "sunny-harbor",
                                "zipCode": "00100",
                            }
                        }
                    }
                ]
            }
        }
    }
