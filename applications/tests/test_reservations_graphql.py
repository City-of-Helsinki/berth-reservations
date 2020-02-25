from string import Template

from graphql_relay.node.node import to_global_id

from berth_reservations.tests.utils import GraphQLTestClient
from harbors.schema import HarborType, WinterStorageAreaType


def test_create_berth_application(boat_type, harbor, berth_switch_reason):
    client = GraphQLTestClient()
    t = Template(
        """
        mutation createBerthApplication {
            createBerthApplication(
                berthSwitch: {
                    harborId: \"${current_harbor}\",
                    pier: "dinkkypier",
                    berthNumber: "D33",
                    reason: ${berth_switch_reason_id}
                },
                berthApplication: {
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
                berthApplication {
                    berthSwitch {
                        berthNumber,
                        reason {
                            id
                        }
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
        berth_switch_reason_id=berth_switch_reason.id,
    )
    executed = client.execute(mutation)
    assert executed == {
        "data": {
            "createBerthApplication": {
                "berthApplication": {
                    "berthSwitch": {
                        "berthNumber": "D33",
                        "reason": {"id": str(berth_switch_reason.id)},
                    },
                    "chosenHarbors": {
                        "edges": [{"node": {"properties": {"zipCode": "00100"}}}]
                    },
                }
            }
        }
    }


def test_create_berth_application_wo_reason(boat_type, harbor):
    client = GraphQLTestClient()
    t = Template(
        """
        mutation createBerthApplication {
            createBerthApplication(
                berthSwitch: {
                    harborId: \"${current_harbor}\",
                    pier: "dinkkypier",
                    berthNumber: "D33",
                },
                berthApplication: {
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
                berthApplication {
                    berthSwitch {
                        berthNumber,
                        reason {
                            id
                        }
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
            "createBerthApplication": {
                "berthApplication": {
                    "berthSwitch": {"berthNumber": "D33", "reason": None},
                    "chosenHarbors": {
                        "edges": [{"node": {"properties": {"zipCode": "00100"}}}]
                    },
                }
            }
        }
    }


def test_create_winter_storage_application(boat_type, winter_area):
    client = GraphQLTestClient()
    t = Template(
        """
        mutation createWinterStorageApplication {
            createWinterStorageApplication(
                winterStorageApplication: {
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
                winterStorageApplication {
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
            "createWinterStorageApplication": {
                "winterStorageApplication": {
                    "chosenAreas": {
                        "edges": [{"node": {"properties": {"zipCode": "00200"}}}]
                    }
                }
            }
        }
    }


def test_get_berth_switch_reasons(berth_switch_reason):
    client = GraphQLTestClient()
    query = """
        {
            berthSwitchReasons {
                id,
                title
            }
        }
    """
    executed = client.execute(query)
    assert executed == {
        "data": {
            "berthSwitchReasons": [
                {"id": str(berth_switch_reason.id), "title": berth_switch_reason.title}
            ]
        }
    }
