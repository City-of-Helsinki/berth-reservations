import uuid

from graphql_relay import to_global_id

from berth_reservations.tests.utils import (
    assert_doesnt_exist,
    assert_field_missing,
    assert_not_enough_permissions,
    GraphQLTestClient,
)
from resources.models import Berth

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


def test_create_berth_no_user(pier, berth_type):
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
        user=None,
    )

    assert Berth.objects.count() == 0
    assert_not_enough_permissions(executed)


def test_create_berth_staff_user(pier, berth_type, staff_user):
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
        user=None,
    )

    assert Berth.objects.count() == 0
    assert_not_enough_permissions(executed)


def test_create_berth_no_number(pier, berth_type, staff_user):
    variables = {
        "pierId": to_global_id("PierNode", str(pier.id)),
        "berthTypeId": to_global_id("BerthTypeNode", str(berth_type.id)),
    }

    assert Berth.objects.count() == 0

    executed = client.execute(
        query=CREATE_BERTH_MUTATION,
        variables=variables,
        graphql_url=GRAPHQL_URL,
        user=None,
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


def test_delete_berth_superuser(superuser, berth):
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


def test_delete_berth_staff_user(staff_user, berth):
    variables = {
        "id": to_global_id("BerthNode", str(berth.id)),
    }

    assert Berth.objects.count() == 1

    executed = client.execute(
        query=DELETE_BERTH_MUTATION,
        variables=variables,
        graphql_url="/graphql_v2/",
        user=staff_user,
    )

    assert Berth.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_delete_berth_no_user(berth):
    variables = {
        "id": to_global_id("BerthNode", str(berth.id)),
    }

    assert Berth.objects.count() == 1

    executed = client.execute(
        query=DELETE_BERTH_MUTATION,
        variables=variables,
        graphql_url="/graphql_v2/",
        user=None,
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
