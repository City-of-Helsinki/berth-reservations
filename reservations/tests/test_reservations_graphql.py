from string import Template

from graphql_relay.node.node import to_global_id

from berth_reservations.tests.utils import GraphQLTestClient
from harbors.schema import HarborType


def test_create_reservation(harbor):
    client = GraphQLTestClient()
    t = Template(
        """
        mutation createReservation {
            createReservation(
                berthSwitch: {
                    harborId: \"${current_harbor}\",
                    pier: "dinkkypier",
                    berthNumber: "D33"
                },
                reservation: {
                    firstName: "John",
                    lastName: "Doe",
                    choices: [
                        {
                            harborId: \"${desired_harbor}\",
                            priority: 1
                        }
                    ]
                }
            ) {
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
    harbor_node_id = to_global_id(HarborType._meta.name, harbor.id)
    mutation = t.substitute(
        current_harbor=harbor_node_id, desired_harbor=harbor_node_id
    )
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
