import json

from berth_reservations.tests.utils import GraphQLTestClient

client = GraphQLTestClient()


def test_get_boat_type(boat_type):
    query = """
        {
            boatTypes {
                name
            }
        }
    """
    executed = client.execute(query=query, graphql_url="/graphql_v2/")
    assert executed["data"] == {"boatTypes": [{"name": boat_type.name}]}


def test_get_harbors(harbor):
    query = """
        {
            harbors {
                edges {
                    node {
                        geometry {
                            type
                            coordinates
                        }
                        properties {
                            name
                            zipCode
                        }
                    }
                }
            }
        }
    """
    executed = client.execute(query=query, graphql_url="/graphql_v2/")
    assert executed["data"] == {
        "harbors": {
            "edges": [
                {
                    "node": {
                        "geometry": json.loads(harbor.location.json),
                        "properties": {"name": harbor.name, "zipCode": harbor.zip_code},
                    }
                }
            ]
        }
    }


def test_get_piers(pier):
    query = """
        {
            piers {
                edges {
                    node {
                        geometry {
                            type
                            coordinates
                        }
                        properties {
                            identifier
                            suitableBoatTypes {
                                name
                            }
                        }
                    }
                }
            }
        }
    """
    executed = client.execute(query=query, graphql_url="/graphql_v2/")
    expected_suitables_boat_types = [
        {"name": bt.name} for bt in pier.suitable_boat_types.all()
    ]
    assert executed["data"] == {
        "piers": {
            "edges": [
                {
                    "node": {
                        "geometry": json.loads(pier.location.json),
                        "properties": {
                            "identifier": pier.identifier,
                            "suitableBoatTypes": expected_suitables_boat_types,
                        },
                    }
                }
            ]
        }
    }


def test_get_berths(berth):
    query = """
        {
            berths {
                edges {
                    node {
                        number
                    }
                }
            }
        }
    """
    executed = client.execute(query=query, graphql_url="/graphql_v2/")
    assert executed["data"] == {
        "berths": {"edges": [{"node": {"number": berth.number}}]}
    }


def test_get_winter_storage_areas(winter_storage_area):
    query = """
        {
            winterStorageAreas {
                edges {
                    node {
                        geometry {
                            type
                            coordinates
                        }
                        properties {
                            name
                            zipCode
                        }
                    }
                }
            }
        }
    """
    executed = client.execute(query=query, graphql_url="/graphql_v2/")
    assert executed["data"] == {
        "winterStorageAreas": {
            "edges": [
                {
                    "node": {
                        "geometry": json.loads(winter_storage_area.location.json),
                        "properties": {
                            "name": winter_storage_area.name,
                            "zipCode": winter_storage_area.zip_code,
                        },
                    }
                }
            ]
        }
    }


def test_get_winter_storage_sections(winter_storage_section):
    query = """
        {
            winterStorageSections {
                edges {
                    node {
                        geometry {
                            type
                            coordinates
                        }
                        properties {
                            identifier
                        }
                    }
                }
            }
        }
    """
    executed = client.execute(query=query, graphql_url="/graphql_v2/")
    assert executed["data"] == {
        "winterStorageSections": {
            "edges": [
                {
                    "node": {
                        "geometry": json.loads(winter_storage_section.location.json),
                        "properties": {"identifier": winter_storage_section.identifier},
                    }
                }
            ]
        }
    }


def test_get_winter_storage_places(winter_storage_place):
    query = """
        {
            winterStoragePlaces {
                edges {
                    node {
                        number
                    }
                }
            }
        }
    """
    executed = client.execute(query=query, graphql_url="/graphql_v2/")
    assert executed["data"] == {
        "winterStoragePlaces": {
            "edges": [{"node": {"number": winter_storage_place.number}}]
        }
    }
