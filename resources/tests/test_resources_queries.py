import json

import pytest
from graphql_relay import to_global_id

from berth_reservations.tests.utils import assert_in_errors, GraphQLTestClient

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


def test_get_piers_filter_by_application(superuser, berth_application, berth):
    query = """
        {
            piers(forApplication: "%s") {
                edges {
                    node {
                        id
                        properties {
                            berths {
                                edges {
                                    node {
                                        berthType {
                                            width
                                            length
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    """ % to_global_id(
        "BerthApplicationNode", berth_application.id
    )

    executed = client.execute(query=query, graphql_url="/graphql_v2/", user=superuser)

    expected_berths = []
    if (
        berth.berth_type.length >= berth_application.boat_length
        and berth.berth_type.width >= berth_application.boat_width
    ):
        expected_berths = [
            {
                "node": {
                    "berthType": {
                        "width": float(berth.berth_type.width),
                        "length": float(berth.berth_type.length),
                    }
                }
            }
        ]

    assert executed["data"] == {
        "piers": {
            "edges": [
                {
                    "node": {
                        "id": to_global_id("PierNode", berth.pier.id),
                        "properties": {"berths": {"edges": expected_berths}},
                    }
                }
            ]
        }
    }


def test_get_piers_filter_error_both_filters(superuser, berth_application, berth):
    query = """
        {
            piers(forApplication: "%s", minBerthWidth: 1.0, minBerthLength: 1.0) {
                edges {
                    node {
                        id
                        properties {
                            berths {
                                edges {
                                    node {
                                        id
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    """ % to_global_id(
        "BerthApplicationNode", berth_application.id
    )

    executed = client.execute(query=query, graphql_url="/graphql_v2/", user=superuser)
    assert_in_errors(
        "You cannot filter by dimension (width, length) and application a the same time",
        executed,
    )


@pytest.mark.parametrize("user", ["none", "base", "staff"], indirect=True)
def test_get_piers_filter_by_application_not_enough_permissions(
    user, berth_application, berth
):
    # To ensure that the values of the Application will always
    # be bigger than the randomly generated by Factory
    berth.berth_type.width = 1.0
    berth.berth_type.length = 1.0
    berth_application.boat_length = 5.0
    berth_application.boat_width = 5.0
    berth.berth_type.save()
    berth_application.save()

    query = """
        {
            piers(forApplication: "%s") {
                edges {
                    node {
                        id
                        properties {
                            berths {
                                edges {
                                    node {
                                        berthType {
                                            width
                                            length
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    """ % to_global_id(
        "BerthApplicationNode", berth_application.id
    )

    expected_berths = [
        {
            "node": {
                "berthType": {
                    "width": float(berth.berth_type.width),
                    "length": float(berth.berth_type.length),
                }
            }
        }
    ]
    executed = client.execute(query=query, graphql_url="/graphql_v2/", user=user)

    assert executed["data"] == {
        "piers": {
            "edges": [
                {
                    "node": {
                        "id": to_global_id("PierNode", berth.pier.id),
                        "properties": {"berths": {"edges": expected_berths}},
                    }
                }
            ]
        }
    }
