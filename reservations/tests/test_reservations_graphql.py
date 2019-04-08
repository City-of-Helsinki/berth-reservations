from string import Template

from graphene.test import Client

from berth_reservations.schema import schema


def test_create_reservation(harbor):
    client = Client(schema)
    t = Template(
        """mutation createReservation {
            createReservation(
                berthSwitch: {
                    harborId: ${harbor},
                    pier: "dinkkypier",
                    berthNumber: "D33"
                },
                reservation: {
                    firstName: "John",
                    lastName: "Doe",
                choices: [
                    { harborId: "sunny-harbor", priority: 1}
                ]
            }) {
            reservation{
                berthSwitch{
                    berthNumber
                },
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
    )
    mutation = t.substitute(harbor=harbor.id)
    executed = client.execute(mutation)
    assert executed == {
        "data": {
            "createReservation": {
                "reservation": {
                    "berthSwitch": {"berthNumber": "D33"},
                    "chosenHarbors": {
                        "edges": [{"node": {"properties": {"zipCode": "00100"}}}]
                    },
                }
            }
        }
    }
