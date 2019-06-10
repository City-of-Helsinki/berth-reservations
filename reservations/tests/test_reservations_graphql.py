from string import Template

from graphql_relay.node.node import to_global_id

from berth_reservations.tests.utils import GraphQLTestClient
from harbors.schema import HarborType, WinterStorageAreaType


def test_create_berth_reservation(boat_type, harbor):
    client = GraphQLTestClient()
    t = Template(
        """
        mutation createBerthReservation {
            createBerthReservation(
                berthSwitch: {
                    harborId: \"${current_harbor}\",
                    pier: "dinkkypier",
                    berthNumber: "D33"
                },
                berthReservation: {
                    language: "en",
                    firstName: "John",
                    lastName: "Doe",
                    phoneNumber: "1234567890",
                    email: "john.doe@example.com",
                    address: "Mannerheimintie 1",
                    zipCode: "00100",
                    municipality: "Helsinki",
                    boatType: ${boat_type_id},
                    boatWidth: 2,
                    boatLength: 3,
                    informationAccuracyConfirmed: true,
                    acceptFitnessNews: false,
                    acceptLibraryNews: false,
                    acceptOtherCultureNews: false,
                    acceptBoatingNewsletter: true,
                    choices: [
                        {
                            harborId: \"${desired_harbor}\",
                            priority: 1
                        }
                    ]
                }
            ) {
                berthReservation {
                    berthSwitch {
                        berthNumber
                    },
                    chosenHarbors {
                        edges {
                            node {
                                properties {
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
        current_harbor=harbor_node_id,
        boat_type_id=boat_type.id,
        desired_harbor=harbor_node_id,
    )
    executed = client.execute(mutation)
    assert executed == {
        "data": {
            "createBerthReservation": {
                "berthReservation": {
                    "berthSwitch": {"berthNumber": "D33"},
                    "chosenHarbors": {
                        "edges": [{"node": {"properties": {"zipCode": "00100"}}}]
                    },
                }
            }
        }
    }


def test_create_winter_storage_reservation(boat_type, winter_area):
    client = GraphQLTestClient()
    t = Template(
        """
        mutation createWinterStorageReservation {
            createWinterStorageReservation(
                winterStorageReservation: {
                    language: "en",
                    firstName: "John",
                    lastName: "Doe",
                    phoneNumber: "1234567890",
                    email: "john.doe@example.com",
                    address: "Mannerheimintie 1",
                    zipCode: "00100",
                    municipality: "Helsinki",
                    boatType: ${boat_type_id},
                    boatWidth: 2,
                    boatLength: 3,
                    informationAccuracyConfirmed: true,
                    acceptFitnessNews: false,
                    acceptLibraryNews: false,
                    acceptOtherCultureNews: false,
                    acceptBoatingNewsletter: true,
                    storageMethod: ON_TRESTLES,
                    chosenAreas: [
                        {
                            winterAreaId: \"${desired_area}\",
                            priority: 1
                        }
                    ]
                }
            ) {
                winterStorageReservation {
                    chosenAreas {
                        edges {
                            node {
                                properties {
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
    winter_area_node_id = to_global_id(WinterStorageAreaType._meta.name, winter_area.id)
    mutation = t.substitute(boat_type_id=boat_type.id, desired_area=winter_area_node_id)
    executed = client.execute(mutation)
    assert executed == {
        "data": {
            "createWinterStorageReservation": {
                "winterStorageReservation": {
                    "chosenAreas": {
                        "edges": [{"node": {"properties": {"zipCode": "00200"}}}]
                    }
                }
            }
        }
    }
