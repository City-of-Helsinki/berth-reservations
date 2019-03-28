from graphene.test import Client

from berth_reservations.schema import schema


def test_create_reservation(harbor):
    client = Client(schema)
    mutation = """
        mutation createReservation {
            createReservation(
                reservation: {
                    firstName: "John",
                    lastName: "Doe",
                choices: [
                    { harborId: "sunny-harbor", priority: 1}
                ]
            }) {
            reservation{
                chosenHarbors{
                    edges{
                    node{
                        properties{
                           zipCode
                        }
                    }
                    }
                }
                }
            }
        }
    """
    executed = client.execute(mutation)
    assert executed == {
        "data": {
            "createReservation": {
                "reservation": {
                    "chosenHarbors": {
                        "edges": [{"node": {"properties": {"zipCode": "00100"}}}]
                    }
                }
            }
        }
    }
