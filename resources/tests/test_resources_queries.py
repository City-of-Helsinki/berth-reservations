import json

import pytest
from graphql_relay import to_global_id

from applications.new_schema import BerthApplicationNode
from berth_reservations.tests.utils import (
    assert_in_errors,
    assert_not_enough_permissions,
)
from leases.schema import BerthLeaseNode
from leases.tests.factories import BerthLeaseFactory
from resources.schema import BerthNode, PierNode


def test_get_boat_type(api_client, boat_type):
    query = """
        {
            boatTypes {
                name
            }
        }
    """
    executed = api_client.execute(query)
    assert executed["data"] == {"boatTypes": [{"name": boat_type.name}]}


def test_get_harbors(api_client, berth):
    harbor = berth.pier.harbor

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
                            maxWidth
                            maxLength
                            maxDepth
                        }
                    }
                }
            }
        }
    """
    executed = api_client.execute(query)
    assert executed["data"] == {
        "harbors": {
            "edges": [
                {
                    "node": {
                        "geometry": json.loads(harbor.location.json),
                        "properties": {
                            "name": harbor.name,
                            "zipCode": harbor.zip_code,
                            "maxWidth": float(berth.berth_type.width),
                            "maxLength": float(berth.berth_type.length),
                            "maxDepth": float(berth.berth_type.depth),
                        },
                    }
                }
            ]
        }
    }


def test_get_piers(api_client, pier):
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
    executed = api_client.execute(query)
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


def test_get_berths(api_client, berth):
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
    executed = api_client.execute(query)
    assert executed["data"] == {
        "berths": {"edges": [{"node": {"number": berth.number}}]}
    }


@pytest.mark.parametrize(
    "api_client",
    ["berth_supervisor", "berth_handler", "berth_services"],
    indirect=True,
)
def test_get_berth_with_leases(api_client, berth):
    berth_lease = BerthLeaseFactory(berth=berth)

    query = """
        {
            berth(id: "%s") {
                leases {
                    edges {
                        node {
                            id
                        }
                    }
                }
            }
        }
    """ % to_global_id(
        BerthNode._meta.name, berth.id
    )
    executed = api_client.execute(query)

    assert executed["data"]["berth"] == {
        "leases": {
            "edges": [
                {
                    "node": {
                        "id": to_global_id(BerthLeaseNode._meta.name, berth_lease.id)
                    }
                }
            ]
        }
    }


@pytest.mark.parametrize(
    "api_client", ["api_client", "user", "harbor_services"], indirect=True,
)
def test_get_berth_with_leases_not_enough_permissions(api_client, berth):
    BerthLeaseFactory(berth=berth)

    query = """
        {
            berth(id: "%s") {
                leases {
                    edges {
                        node {
                            id
                        }
                    }
                }
            }
        }
    """ % to_global_id(
        BerthNode._meta.name, berth.id
    )
    executed = api_client.execute(query)
    assert_not_enough_permissions(executed)


def test_get_winter_storage_areas(api_client, winter_storage_area):
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
    executed = api_client.execute(query)
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


def test_get_winter_storage_sections(api_client, winter_storage_section):
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
    executed = api_client.execute(query)
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


def test_get_winter_storage_places(api_client, winter_storage_place):
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
    executed = api_client.execute(query)
    assert executed["data"] == {
        "winterStoragePlaces": {
            "edges": [{"node": {"number": winter_storage_place.number}}]
        }
    }


@pytest.mark.parametrize(
    "api_client",
    ["berth_supervisor", "berth_handler", "berth_services"],
    indirect=True,
)
def test_get_piers_filter_by_application(api_client, berth_application, berth):
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
        BerthApplicationNode._meta.name, berth_application.id
    )

    executed = api_client.execute(query)

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
                        "id": to_global_id(PierNode._meta.name, berth.pier.id),
                        "properties": {"berths": {"edges": expected_berths}},
                    }
                }
            ]
        }
    }


@pytest.mark.parametrize(
    "api_client",
    ["berth_supervisor", "berth_handler", "berth_services"],
    indirect=True,
)
def test_get_piers_filter_error_both_filters(api_client, berth_application, berth):
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
        BerthApplicationNode._meta.name, berth_application.id
    )

    executed = api_client.execute(query)

    assert_in_errors(
        "You cannot filter by dimension (width, length) and application a the same time",
        executed,
    )


@pytest.mark.parametrize(
    "api_client", ["api_client", "user", "harbor_services"], indirect=True,
)
def test_get_piers_filter_by_application_not_enough_permissions(
    api_client, berth_application
):
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
        BerthApplicationNode._meta.name, berth_application.id
    )

    executed = api_client.execute(query)

    assert_not_enough_permissions(executed)
