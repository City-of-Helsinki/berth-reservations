import uuid

import pytest
from graphql_relay import to_global_id

from berth_reservations.tests.utils import (
    assert_doesnt_exist,
    assert_field_duplicated,
    assert_field_missing,
    assert_invalid_enum,
    assert_not_enough_permissions,
    GraphQLTestClient,
)
from resources.models import Berth, BerthType, Harbor, Pier

client = GraphQLTestClient()

GRAPHQL_URL = "/graphql_v2/"


CREATE_BERTH_MUTATION = """
    mutation CreateBerth($input: CreateBerthMutationInput!) {
      createBerth(input: $input) {
        berth {
          id
          number
          comment
        }
      }
    }
"""


def test_create_berth(pier, berth_type, superuser):
    variables = {
        "number": "9999",
        "comment": "foobar",
        "pierId": to_global_id("PierNode", str(pier.id)),
        "berthTypeId": to_global_id("BerthTypeNode", str(berth_type.id)),
    }

    assert Berth.objects.count() == 0

    executed = client.execute(
        query=CREATE_BERTH_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert Berth.objects.count() == 1
    assert executed["data"]["createBerth"]["berth"]["id"] is not None
    assert executed["data"]["createBerth"]["berth"]["comment"] == "foobar"
    assert executed["data"]["createBerth"]["berth"]["number"] == "9999"


@pytest.mark.parametrize("user", ["none", "base", "staff"], indirect=True)
def test_create_berth_not_enough_permissions(user, pier, berth_type):
    variables = {
        "number": "9999",
        "comment": "foobar",
        "pierId": to_global_id("PierNode", str(pier.id)),
        "berthTypeId": to_global_id("BerthTypeNode", str(berth_type.id)),
    }

    assert Berth.objects.count() == 0

    executed = client.execute(
        query=CREATE_BERTH_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=user,
    )

    assert Berth.objects.count() == 0
    assert_not_enough_permissions(executed)


def test_create_berth_no_number(pier, berth_type, superuser):
    variables = {
        "pierId": to_global_id("PierNode", str(pier.id)),
        "berthTypeId": to_global_id("BerthTypeNode", str(berth_type.id)),
    }

    assert Berth.objects.count() == 0

    executed = client.execute(
        query=CREATE_BERTH_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert Berth.objects.count() == 0
    assert_field_missing("number", executed)


DELETE_BERTH_MUTATION = """
    mutation DeleteBerth($input: DeleteBerthMutationInput!) {
      deleteBerth(input: $input) {
        __typename
      }
    }
"""


def test_delete_berth(superuser, berth):
    variables = {
        "id": to_global_id("BerthNode", str(berth.id)),
    }

    assert Berth.objects.count() == 1

    client.execute(
        query=DELETE_BERTH_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert Berth.objects.count() == 0


@pytest.mark.parametrize("user", ["none", "base", "staff"], indirect=True)
def test_delete_berth_not_enough_permissions(user, berth):
    variables = {
        "id": to_global_id("BerthNode", str(berth.id)),
    }

    assert Berth.objects.count() == 1

    executed = client.execute(
        query=DELETE_BERTH_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=user,
    )

    assert Berth.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_delete_berth_inexistent_berth(superuser):
    variables = {
        "id": to_global_id("BerthNode", uuid.uuid4()),
    }

    executed = client.execute(
        query=DELETE_BERTH_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert_doesnt_exist("Berth", executed)


UPDATE_BERTH_MUTATION = """
    mutation UpdateBerth($input: UpdateBerthMutationInput!) {
      updateBerth(input: $input) {
        berth {
          id
          number
          comment
          pier {
            id
          }
          berthType {
            id
          }
        }
      }
    }
"""


def test_update_berth(berth, pier, berth_type, superuser):
    global_id = to_global_id("BerthNode", str(berth.id))
    pier_id = to_global_id("PierNode", str(pier.id))
    berth_type_id = to_global_id("BerthTypeNode", str(berth_type.id))

    variables = {
        "id": global_id,
        "number": "666",
        "comment": "foobar",
        "pierId": pier_id,
        "berthTypeId": berth_type_id,
    }

    assert Berth.objects.count() == 1

    executed = client.execute(
        query=UPDATE_BERTH_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert Berth.objects.count() == 1
    assert executed["data"]["updateBerth"]["berth"]["id"] == global_id
    assert executed["data"]["updateBerth"]["berth"]["comment"] == "foobar"
    assert executed["data"]["updateBerth"]["berth"]["number"] == "666"
    assert executed["data"]["updateBerth"]["berth"]["pier"]["id"] == pier_id
    assert executed["data"]["updateBerth"]["berth"]["berthType"]["id"] == berth_type_id


def test_update_berth_no_id(berth, pier, berth_type, superuser):
    pier_id = to_global_id("PierNode", str(pier.id))
    berth_type_id = to_global_id("BerthTypeNode", str(berth_type.id))

    variables = {
        "number": "666",
        "comment": "foobar",
        "pierId": pier_id,
        "berthTypeId": berth_type_id,
    }

    assert Berth.objects.count() == 1

    executed = client.execute(
        query=UPDATE_BERTH_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert Berth.objects.count() == 1
    assert_field_missing("id", executed)


@pytest.mark.parametrize("user", ["none", "base", "staff"], indirect=True)
def test_update_berth_not_enough_permissions(berth, pier, berth_type, user):
    pier_id = to_global_id("PierNode", str(pier.id))
    berth_type_id = to_global_id("BerthTypeNode", str(berth_type.id))

    variables = {
        "number": "666",
        "comment": "foobar",
        "pierId": pier_id,
        "berthTypeId": berth_type_id,
    }
    assert Berth.objects.count() == 1

    executed = client.execute(
        query=CREATE_BERTH_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=user,
    )

    assert Berth.objects.count() == 1
    assert_not_enough_permissions(executed)


CREATE_BERTH_TYPE_MUTATION = """
mutation CreateBerthTypeMutation($input: CreateBerthTypeMutationInput!) {
  createBerthType(input: $input) {
    berthType {
      id
      width
      length
      mooringType
    }
  }
}
"""


def test_create_berth_type(superuser):
    variables = {"mooringType": "DINGHY_PLACE", "width": 666, "length": 333}

    assert BerthType.objects.count() == 0

    executed = client.execute(
        query=CREATE_BERTH_TYPE_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert BerthType.objects.count() == 1
    assert executed["data"]["createBerthType"]["berthType"]["id"] is not None
    assert (
        executed["data"]["createBerthType"]["berthType"]["mooringType"]
        == variables["mooringType"]
    )
    assert (
        executed["data"]["createBerthType"]["berthType"]["width"] == variables["width"]
    )
    assert (
        executed["data"]["createBerthType"]["berthType"]["length"]
        == variables["length"]
    )


@pytest.mark.parametrize("user", ["none", "base", "staff"], indirect=True)
def test_create_berth_type_not_enough_permissions(user):
    variables = {"mooringType": "DINGHY_PLACE", "width": 666, "length": 333}

    assert BerthType.objects.count() == 0

    executed = client.execute(
        query=CREATE_BERTH_TYPE_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=user,
    )

    assert BerthType.objects.count() == 0
    assert_not_enough_permissions(executed)


def test_create_berth_type_invalid_mooring(superuser):
    variables = {"mooringType": "INVALID_VALUE", "width": 666, "length": 333}

    assert BerthType.objects.count() == 0

    executed = client.execute(
        query=CREATE_BERTH_TYPE_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert BerthType.objects.count() == 0

    assert_invalid_enum("mooringType", "BerthMooringType", executed)


DELETE_BERTH_TYPE_MUTATION = """
    mutation DeleteBerthType($input: DeleteBerthTypeMutationInput!) {
      deleteBerthType(input: $input) {
        __typename
      }
    }
"""


def test_delete_berth_type(superuser, berth_type):
    variables = {
        "id": to_global_id("BerthTypeNode", str(berth_type.id)),
    }

    assert BerthType.objects.count() == 1

    client.execute(
        query=DELETE_BERTH_TYPE_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert BerthType.objects.count() == 0


@pytest.mark.parametrize("user", ["none", "base", "staff"], indirect=True)
def test_delete_berth_type_not_enough_permissions(user, berth_type):
    variables = {
        "id": to_global_id("BerthTypeNode", str(berth_type.id)),
    }

    assert BerthType.objects.count() == 1

    executed = client.execute(
        query=DELETE_BERTH_TYPE_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=user,
    )

    assert BerthType.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_delete_berth_type_inexistent_berth(superuser):
    variables = {
        "id": to_global_id("BerthTypeNode", uuid.uuid4()),
    }

    executed = client.execute(
        query=DELETE_BERTH_TYPE_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert_doesnt_exist("BerthType", executed)


UPDATE_BERTH_TYPE_MUTATION = """
  mutation UpdateBerthTypeMutation($input: UpdateBerthTypeMutationInput!){
    updateBerthType(input: $input) {
      berthType {
        id
        width
        length
        mooringType
      }
    }
  }
"""


def test_update_berth_type(berth_type, superuser):
    global_id = to_global_id("BerthTypeNode", str(berth_type.id))

    variables = {
        "id": global_id,
        "width": 999,
        "length": 999,
        "mooringType": "QUAYSIDE_MOORING",
    }

    assert BerthType.objects.count() == 1

    executed = client.execute(
        query=UPDATE_BERTH_TYPE_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert BerthType.objects.count() == 1
    assert executed["data"]["updateBerthType"]["berthType"]["id"] == global_id
    assert (
        executed["data"]["updateBerthType"]["berthType"]["width"] == variables["width"]
    )
    assert (
        executed["data"]["updateBerthType"]["berthType"]["length"]
        == variables["length"]
    )
    assert (
        executed["data"]["updateBerthType"]["berthType"]["mooringType"]
        == variables["mooringType"]
    )


def test_update_berth_type_no_id(superuser, berth_type):
    variables = {
        "width": 999,
        "length": 999,
    }

    assert BerthType.objects.count() == 1

    executed = client.execute(
        query=UPDATE_BERTH_TYPE_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert BerthType.objects.count() == 1
    assert_field_missing("id", executed)


@pytest.mark.parametrize("user", ["none", "base", "staff"], indirect=True)
def test_update_berth_type_not_enough_permissions(user, berth_type):
    variables = {
        "id": to_global_id("BerthTypeNode", str(berth_type.id)),
    }
    assert BerthType.objects.count() == 1

    executed = client.execute(
        query=UPDATE_BERTH_TYPE_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=user,
    )

    assert BerthType.objects.count() == 1
    assert_not_enough_permissions(executed)


CREATE_HARBOR_MUTATION = """
mutation CreateHarbor($input: CreateHarborMutationInput!) {
  createHarbor(input: $input) {
    harbor {
      id
      type
      geometry {
        type
        coordinates
      }
      bbox
      properties {
        name
        servicemapId
        streetAddress
        zipCode
        availabilityLevel {
          id
        }
        municipality
        numberOfPlaces
        maximumWidth
        maximumLength
        maximumDepth
      }
    }
  }
}
"""


def test_create_harbor(superuser, availability_level, municipality):
    variables = {
        "imageFile": "image.png",
        "availabilityLevelId": availability_level.id,
        "municipalityId": municipality.id,
        "numberOfPlaces": 150,
        "maximumWidth": 350,
        "maximumLength": 400,
        "maximumDepth": 100,
        "name": "Foobarsatama",
        "streetAddress": "Foobarstatmanrantatie 1234",
        "servicemapId": "1",
        "zipCode": "00100",
        "location": {"type": "Point", "coordinates": [66.6, 99.9]},
    }

    assert Harbor.objects.count() == 0

    executed = client.execute(
        query=CREATE_HARBOR_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        lang="en",
        user=superuser,
    )

    assert Harbor.objects.count() == 1
    assert executed["data"]["createHarbor"]["harbor"]["id"] is not None
    assert executed["data"]["createHarbor"]["harbor"]["geometry"] == {
        "type": variables["location"]["type"],
        "coordinates": variables["location"]["coordinates"],
    }
    assert executed["data"]["createHarbor"]["harbor"]["bbox"] == [
        variables["location"]["coordinates"][0],
        variables["location"]["coordinates"][1],
        variables["location"]["coordinates"][0],
        variables["location"]["coordinates"][1],
    ]
    assert executed["data"]["createHarbor"]["harbor"]["properties"] == {
        "name": variables["name"],
        "servicemapId": variables["servicemapId"],
        "streetAddress": variables["streetAddress"],
        "zipCode": variables["zipCode"],
        "availabilityLevel": {"id": str(availability_level.id)},
        "municipality": municipality.name,
        "numberOfPlaces": variables["numberOfPlaces"],
        "maximumWidth": variables["maximumWidth"],
        "maximumLength": variables["maximumLength"],
        "maximumDepth": variables["maximumDepth"],
    }


@pytest.mark.parametrize("user", ["none", "base", "staff"], indirect=True)
def test_create_harbor_not_enough_permissions(user):
    variables = {"name": "Foobarsatama"}

    assert Harbor.objects.count() == 0

    executed = client.execute(
        query=CREATE_HARBOR_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=user,
    )

    assert Harbor.objects.count() == 0
    assert_not_enough_permissions(executed)


def test_create_harbor_availability_level_doesnt_exist(superuser):
    variables = {"availabilityLevelId": "9999"}

    assert Harbor.objects.count() == 0

    executed = client.execute(
        query=CREATE_HARBOR_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert Harbor.objects.count() == 0
    assert_doesnt_exist("AvailabilityLevel", executed)


def test_create_harbor_municipality_doesnt_exist(superuser):
    variables = {"municipalityId": "foobarland"}

    assert Harbor.objects.count() == 0

    executed = client.execute(
        query=CREATE_HARBOR_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert Harbor.objects.count() == 0
    assert_doesnt_exist("Municipality", executed)


def test_create_harbor_duplicated_servicemap_id(superuser, harbor):
    variables = {"servicemapId": str(harbor.servicemap_id)}

    assert Harbor.objects.count() == 1

    executed = client.execute(
        query=CREATE_HARBOR_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert Harbor.objects.count() == 1
    assert_field_duplicated("servicemap_id", executed)


DELETE_HARBOR_MUTATION = """
    mutation DeleteHarbor($input: DeleteHarborMutationInput!) {
      deleteHarbor(input: $input) {
        __typename
      }
    }
"""


def test_delete_harbor(superuser, harbor):
    variables = {
        "id": to_global_id("HarborNode", str(harbor.id)),
    }

    assert Harbor.objects.count() == 1

    client.execute(
        query=DELETE_HARBOR_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert Harbor.objects.count() == 0


@pytest.mark.parametrize("user", ["none", "base", "staff"], indirect=True)
def test_delete_harbor_not_enough_permissions(user, harbor):
    variables = {
        "id": to_global_id("HarborNode", str(harbor.id)),
    }

    assert Harbor.objects.count() == 1

    executed = client.execute(
        query=DELETE_HARBOR_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=user,
    )

    assert Harbor.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_delete_harbor_inexistent_harbor(superuser):
    variables = {
        "id": to_global_id("HarborNode", uuid.uuid4()),
    }

    executed = client.execute(
        query=DELETE_HARBOR_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert_doesnt_exist("Harbor", executed)


UPDATE_HARBOR_MUTATION = """
mutation UpdateHarbor($input: UpdateHarborMutationInput!) {
  updateHarbor(input: $input) {
    harbor {
      id
      type
      geometry {
        type
        coordinates
      }
      bbox
      properties {
        name
        servicemapId
        streetAddress
        zipCode
        availabilityLevel {
          id
        }
        municipality
        numberOfPlaces
        maximumWidth
        maximumLength
        maximumDepth
      }
    }
  }
}
"""


def test_update_harbor(superuser, harbor, availability_level, municipality):
    global_id = to_global_id("HarborNode", str(harbor.id))

    variables = {
        "id": global_id,
        "imageFile": "image.png",
        "availabilityLevelId": availability_level.id,
        "municipalityId": municipality.id,
        "numberOfPlaces": 175,
        "maximumWidth": 400,
        "maximumLength": 550,
        "maximumDepth": 200,
        "name": "Uusi Foobarsatama",
        "streetAddress": "Uusifoobarstatmanrantatie 2345",
        "servicemapId": "1",
        "zipCode": "10101",
        "location": {"type": "Point", "coordinates": [99.9, 66.6]},
    }

    assert Harbor.objects.count() == 1

    executed = client.execute(
        query=UPDATE_HARBOR_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        lang="en",
        user=superuser,
    )

    assert Harbor.objects.count() == 1
    assert executed["data"]["updateHarbor"]["harbor"]["id"] == global_id
    assert executed["data"]["updateHarbor"]["harbor"]["geometry"] == {
        "type": variables["location"]["type"],
        "coordinates": variables["location"]["coordinates"],
    }
    assert executed["data"]["updateHarbor"]["harbor"]["bbox"] == [
        variables["location"]["coordinates"][0],
        variables["location"]["coordinates"][1],
        variables["location"]["coordinates"][0],
        variables["location"]["coordinates"][1],
    ]
    assert executed["data"]["updateHarbor"]["harbor"]["properties"] == {
        "name": variables["name"],
        "servicemapId": variables["servicemapId"],
        "streetAddress": variables["streetAddress"],
        "zipCode": variables["zipCode"],
        "availabilityLevel": {"id": str(availability_level.id)},
        "municipality": municipality.name,
        "numberOfPlaces": variables["numberOfPlaces"],
        "maximumWidth": variables["maximumWidth"],
        "maximumLength": variables["maximumLength"],
        "maximumDepth": variables["maximumDepth"],
    }


def test_update_harbor_no_id(superuser, harbor):
    variables = {"name": "Uusi Foobarsatama"}

    assert Harbor.objects.count() == 1

    executed = client.execute(
        query=UPDATE_HARBOR_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert Harbor.objects.count() == 1
    assert_field_missing("id", executed)


@pytest.mark.parametrize("user", ["none", "base", "staff"], indirect=True)
def test_update_harbor_not_enough_permissions(user, harbor):
    variables = {
        "id": to_global_id("HarborNode", str(harbor.id)),
    }
    assert Harbor.objects.count() == 1

    executed = client.execute(
        query=UPDATE_HARBOR_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=user,
    )

    assert Harbor.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_update_harbor_availability_level_doesnt_exist(harbor, superuser):
    variables = {
        "id": to_global_id("HarborNode", harbor.id),
        "availabilityLevelId": "9999",
    }

    assert Harbor.objects.count() == 1

    executed = client.execute(
        query=UPDATE_HARBOR_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )
    print(executed)

    assert Harbor.objects.count() == 1
    assert_doesnt_exist("AvailabilityLevel", executed)


def test_update_harbor_municipality_doesnt_exist(harbor, superuser):
    variables = {
        "id": to_global_id("HarborNode", harbor.id),
        "municipalityId": "foobarland",
    }

    assert Harbor.objects.count() == 1

    executed = client.execute(
        query=UPDATE_HARBOR_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert Harbor.objects.count() == 1
    assert_doesnt_exist("Municipality", executed)


CREATE_PIER_MUTATION = """
mutation CreatePier($input: CreatePierMutationInput!) {
  createPier(input: $input) {
    pier {
      id
      properties {
        harbor {
          id
        }
        identifier
        electricity
        gate
        lighting
        mooring
        water
        wasteCollection
        suitableBoatTypes {
          id
        }
      }
    }
  }
}
"""


def test_create_pier(superuser, harbor, boat_type):
    harbor_id = to_global_id("HarborNode", harbor.id)
    boat_types = [boat_type.id]

    variables = {
        "harborId": harbor_id,
        "lighting": True,
        "wasteCollection": True,
        "mooring": True,
        "suitableBoatTypes": boat_types,
        "identifier": "foobar",
        "location": {"type": "Point", "coordinates": [66.6, 99.9]},
        "water": True,
        "electricity": True,
        "gate": True,
    }
    assert Pier.objects.count() == 0

    executed = client.execute(
        query=CREATE_PIER_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert Pier.objects.count() == 1
    assert executed["data"]["createPier"]["pier"]["id"] is not None
    assert executed["data"]["createPier"]["pier"]["properties"] == {
        "harbor": {"id": harbor_id},
        "identifier": variables["identifier"],
        "electricity": variables["electricity"],
        "gate": variables["gate"],
        "lighting": variables["lighting"],
        "mooring": variables["mooring"],
        "water": variables["water"],
        "wasteCollection": variables["wasteCollection"],
        "suitableBoatTypes": [{"id": str(boat_type.id)}],
    }


@pytest.mark.parametrize("user", ["none", "base", "staff"], indirect=True)
def test_create_pier_not_enough_permissions(user):
    variables = {"harborId": ""}

    assert Pier.objects.count() == 0

    executed = client.execute(
        query=CREATE_PIER_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=user,
    )

    assert Pier.objects.count() == 0
    assert_not_enough_permissions(executed)


def test_create_harbor_harbor_doesnt_exist(superuser):
    variables = {"harborId": to_global_id("BerthNode", uuid.uuid4())}

    assert Pier.objects.count() == 0

    executed = client.execute(
        query=CREATE_PIER_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert Pier.objects.count() == 0
    assert_doesnt_exist("Harbor", executed)


def test_create_pier_no_harbor(superuser):
    variables = {"identifier": "foo"}

    assert Pier.objects.count() == 0

    executed = client.execute(
        query=CREATE_PIER_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=superuser,
    )

    assert Pier.objects.count() == 0
    assert_field_missing("harborId", executed)
