import uuid

import pytest
from graphql_relay import to_global_id

from berth_reservations.tests.utils import (
    assert_doesnt_exist,
    assert_field_missing,
    assert_invalid_enum,
    assert_not_enough_permissions,
    GraphQLTestClient,
)
from resources.models import Berth, BerthType

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
        graphql_url="/graphql_v2/",
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
        graphql_url="/graphql_v2/",
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
        graphql_url="/graphql_v2/",
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
        graphql_url="/graphql_v2/",
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
        graphql_url="/graphql_v2/",
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
        graphql_url="/graphql_v2/",
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
        graphql_url="/graphql_v2/",
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
        graphql_url="/graphql_v2/",
        user=superuser,
    )

    assert_doesnt_exist("BerthType", executed)
