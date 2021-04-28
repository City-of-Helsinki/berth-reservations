import decimal
import random
import uuid

import pytest
from graphql_relay import from_global_id, to_global_id

from berth_reservations.tests.utils import (
    assert_doesnt_exist,
    assert_field_duplicated,
    assert_field_missing,
    assert_in_errors,
    assert_not_enough_permissions,
)
from leases.enums import LeaseStatus
from leases.tests.factories import BerthLeaseFactory, WinterStorageLeaseFactory
from payments.enums import PriceTier

from ..enums import BerthMooringType
from ..models import (
    Berth,
    BerthType,
    Harbor,
    Pier,
    WinterStorageArea,
    WinterStoragePlace,
    WinterStoragePlaceType,
    WinterStorageSection,
)
from ..schema import (
    BerthNode,
    HarborNode,
    PierNode,
    WinterStorageAreaNode,
    WinterStoragePlaceNode,
    WinterStoragePlaceTypeNode,
    WinterStorageSectionNode,
)
from .factories import BerthTypeFactory, WinterStoragePlaceFactory

CREATE_BERTH_MUTATION = """
mutation CreateBerth($input: CreateBerthMutationInput!) {
    createBerth(input: $input) {
        berth {
            id
            number
            comment
            isAccessible
            isActive
            width
            length
            depth
            mooringType
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_create_berth(pier, api_client, berth_type):
    variables = {
        "number": "9999",
        "comment": "foobar",
        "pierId": to_global_id(PierNode._meta.name, str(pier.id)),
        "isActive": False,
        "width": float(berth_type.width),
        "length": float(berth_type.length),
        "depth": float(berth_type.depth),
        "mooringType": berth_type.mooring_type.name,
    }

    assert Berth.objects.count() == 0
    assert BerthType.objects.count() == 1

    executed = api_client.execute(CREATE_BERTH_MUTATION, input=variables)

    assert Berth.objects.count() == 1
    # Check that no more berth types were created
    assert BerthType.objects.count() == 1
    assert executed["data"]["createBerth"]["berth"].pop("id") is not None

    assert executed["data"]["createBerth"]["berth"] == {
        "comment": "foobar",
        "number": "9999",
        "isAccessible": None,
        "isActive": False,
        "width": variables["width"],
        "length": variables["length"],
        "depth": variables["depth"],
        "mooringType": variables["mooringType"],
    }


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_create_berth_new_berth_type(pier, api_client):
    variables = {
        "number": "9999",
        "comment": "foobar",
        "pierId": to_global_id(PierNode._meta.name, str(pier.id)),
        "isActive": False,
        "width": round(random.uniform(1.5, 99.0), 2),
        "length": round(random.uniform(1.5, 99.0), 2),
        "depth": round(random.uniform(1.5, 99.0), 2),
        "mooringType": random.choice(list(BerthMooringType)).name,
    }

    assert Berth.objects.count() == 0
    assert BerthType.objects.count() == 0

    executed = api_client.execute(CREATE_BERTH_MUTATION, input=variables)

    assert Berth.objects.count() == 1
    assert BerthType.objects.count() == 1

    assert executed["data"]["createBerth"]["berth"].pop("id") is not None

    assert executed["data"]["createBerth"]["berth"] == {
        "comment": "foobar",
        "number": "9999",
        "isAccessible": None,
        "isActive": False,
        "width": variables["width"],
        "length": variables["length"],
        "depth": variables["depth"],
        "mooringType": variables["mooringType"],
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_create_berth_not_enough_permissions(api_client, pier, berth_type):
    variables = {
        "number": "9999",
        "comment": "foobar",
        "pierId": to_global_id(PierNode._meta.name, str(pier.id)),
        "width": float(berth_type.width),
        "length": float(berth_type.length),
        "mooringType": berth_type.mooring_type.name,
    }

    assert Berth.objects.count() == 0

    executed = api_client.execute(CREATE_BERTH_MUTATION, input=variables)

    assert Berth.objects.count() == 0
    assert_not_enough_permissions(executed)


def test_create_berth_no_number(pier, berth_type, superuser_api_client):
    variables = {
        "pierId": to_global_id(PierNode._meta.name, str(pier.id)),
    }

    assert Berth.objects.count() == 0

    executed = superuser_api_client.execute(CREATE_BERTH_MUTATION, input=variables)

    assert Berth.objects.count() == 0
    assert_field_missing("number", executed)


@pytest.mark.parametrize("missing_field", ["width", "length", "mooringType"])
def test_create_berth_missing_berth_type_params(
    superuser_api_client, missing_field, pier
):
    variables = {
        "number": "9999",
        "pierId": to_global_id(PierNode._meta.name, str(pier.id)),
        "width": round(random.uniform(1.5, 99.0), 2),
        "length": round(random.uniform(1.5, 99.0), 2),
        "mooringType": random.choice(list(BerthMooringType)).name,
    }
    del variables[missing_field]

    assert Berth.objects.count() == 0
    assert BerthType.objects.count() == 0

    executed = superuser_api_client.execute(CREATE_BERTH_MUTATION, input=variables)

    assert Berth.objects.count() == 0
    assert BerthType.objects.count() == 0

    assert_field_missing(missing_field, executed)


DELETE_BERTH_MUTATION = """
mutation DeleteBerth($input: DeleteBerthMutationInput!) {
    deleteBerth(input: $input) {
        __typename
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_delete_berth(api_client, berth):
    variables = {
        "id": to_global_id(BerthNode._meta.name, str(berth.id)),
    }

    assert Berth.objects.count() == 1

    api_client.execute(DELETE_BERTH_MUTATION, input=variables)

    assert Berth.objects.count() == 0


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_delete_berth_not_enough_permissions(api_client, berth):
    variables = {
        "id": to_global_id(BerthNode._meta.name, str(berth.id)),
    }

    assert Berth.objects.count() == 1

    executed = api_client.execute(DELETE_BERTH_MUTATION, input=variables)

    assert Berth.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_delete_berth_inexistent_berth(superuser_api_client):
    variables = {
        "id": to_global_id(BerthNode._meta.name, uuid.uuid4()),
    }

    executed = superuser_api_client.execute(DELETE_BERTH_MUTATION, input=variables)

    assert_doesnt_exist("Berth", executed)


def test_delete_berth_with_lease(superuser_api_client, berth):
    berth_lease = BerthLeaseFactory(berth=berth, status=LeaseStatus.DRAFTED)
    variables = {
        "id": to_global_id(BerthNode._meta.name, berth_lease.berth.id),
    }

    assert Berth.objects.count() == 1

    superuser_api_client.execute(DELETE_BERTH_MUTATION, input=variables)

    assert Berth.objects.count() == 0


def test_delete_berth_protected_with_lease(superuser_api_client, berth):
    berth_lease = BerthLeaseFactory(berth=berth, status=LeaseStatus.PAID)
    variables = {
        "id": to_global_id(BerthNode._meta.name, berth_lease.berth.id),
    }

    executed = superuser_api_client.execute(DELETE_BERTH_MUTATION, input=variables)

    assert_in_errors(
        "Cannot delete Berth because it has some related leases", executed,
    )


UPDATE_BERTH_MUTATION = """
mutation UpdateBerth($input: UpdateBerthMutationInput!) {
    updateBerth(input: $input) {
        berth {
            id
            number
            comment
            isAccessible
            isActive
            pier {
                id
            }
            width
            length
            depth
            mooringType
            isInvoiceable
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_update_berth(berth, pier, api_client):
    global_id = to_global_id(BerthNode._meta.name, str(berth.id))
    pier_id = to_global_id(PierNode._meta.name, str(pier.id))

    variables = {
        "id": global_id,
        "number": "666",
        "comment": "foobar",
        "isAccessible": True,
        "pierId": pier_id,
        "isActive": False,
    }

    assert Berth.objects.count() == 1

    executed = api_client.execute(UPDATE_BERTH_MUTATION, input=variables)

    assert Berth.objects.count() == 1
    assert executed["data"]["updateBerth"]["berth"] == {
        "id": global_id,
        "comment": variables["comment"],
        "number": "666",
        "isAccessible": variables["isAccessible"],
        "pier": {"id": variables["pierId"]},
        "isActive": variables["isActive"],
        "width": float(berth.berth_type.width),
        "length": float(berth.berth_type.length),
        "depth": float(berth.berth_type.depth),
        "mooringType": berth.berth_type.mooring_type.name,
        "isInvoiceable": berth.is_invoiceable,
    }


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_update_berth_existing_berth_type(berth, pier, berth_type, api_client):
    global_id = to_global_id(BerthNode._meta.name, str(berth.id))

    variables = {
        "id": global_id,
        "width": float(berth_type.width),
        "length": float(berth_type.length),
        "depth": float(berth_type.depth),
        "mooringType": berth_type.mooring_type.name,
    }

    assert berth.berth_type != berth_type
    assert Berth.objects.count() == 1
    assert BerthType.objects.count() == 2

    executed = api_client.execute(UPDATE_BERTH_MUTATION, input=variables)

    assert Berth.objects.count() == 1
    assert BerthType.objects.count() == 2

    assert executed["data"]["updateBerth"]["berth"] == {
        "id": global_id,
        "comment": berth.comment,
        "number": berth.number,
        "isAccessible": berth.is_accessible,
        "pier": {"id": to_global_id(PierNode._meta.name, berth.pier.id)},
        "isActive": berth.is_active,
        "width": variables["width"],
        "length": variables["length"],
        "depth": variables["depth"],
        "mooringType": variables["mooringType"],
        "isInvoiceable": berth.is_invoiceable,
    }
    assert Berth.objects.get(id=berth.id).berth_type == berth_type


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_update_berth_existing_berth_type_null_depth(berth, pier, api_client):
    global_id = to_global_id(BerthNode._meta.name, str(berth.id))
    berth_type = BerthTypeFactory(depth=None)

    variables = {
        "id": global_id,
        "width": float(berth_type.width),
        "length": float(berth_type.length),
        "depth": berth_type.depth,
        "mooringType": berth_type.mooring_type.name,
    }

    assert berth.berth_type != berth_type
    assert Berth.objects.count() == 1
    assert BerthType.objects.count() == 2

    executed = api_client.execute(UPDATE_BERTH_MUTATION, input=variables)

    assert Berth.objects.count() == 1
    assert BerthType.objects.count() == 2

    assert executed["data"]["updateBerth"]["berth"] == {
        "id": global_id,
        "comment": berth.comment,
        "number": berth.number,
        "isAccessible": berth.is_accessible,
        "pier": {"id": to_global_id(PierNode._meta.name, berth.pier.id)},
        "isActive": berth.is_active,
        "width": variables["width"],
        "length": variables["length"],
        "depth": variables["depth"],
        "mooringType": variables["mooringType"],
        "isInvoiceable": berth.is_invoiceable,
    }
    assert Berth.objects.get(id=berth.id).berth_type == berth_type
    assert Berth.objects.get(id=berth.id).berth_type.depth is None


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_update_berth_existing_berth_type_only_depth(berth, pier, api_client):
    global_id = to_global_id(BerthNode._meta.name, str(berth.id))

    variables = {
        "id": global_id,
        "depth": round(random.uniform(1.5, 99.0), 2),
    }

    assert Berth.objects.count() == 1
    assert BerthType.objects.count() == 1

    executed = api_client.execute(UPDATE_BERTH_MUTATION, input=variables)

    assert Berth.objects.count() == 1
    assert BerthType.objects.count() == 2

    assert executed["data"]["updateBerth"]["berth"] == {
        "id": global_id,
        "comment": berth.comment,
        "number": berth.number,
        "isAccessible": berth.is_accessible,
        "pier": {"id": to_global_id(PierNode._meta.name, berth.pier.id)},
        "isActive": berth.is_active,
        "width": float(berth.berth_type.width),
        "length": float(berth.berth_type.length),
        "depth": variables["depth"],
        "mooringType": berth.berth_type.mooring_type.name,
        "isInvoiceable": berth.is_invoiceable,
    }


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_update_berth_new_berth_type(berth, pier, api_client):
    global_id = to_global_id(BerthNode._meta.name, str(berth.id))

    variables = {
        "id": global_id,
        "width": round(random.uniform(1.5, 99.0), 2),
        "length": round(random.uniform(1.5, 99.0), 2),
        "depth": round(random.uniform(1.5, 99.0), 2),
        "mooringType": random.choice(list(BerthMooringType)).name,
    }

    assert Berth.objects.count() == 1
    assert BerthType.objects.count() == 1

    executed = api_client.execute(UPDATE_BERTH_MUTATION, input=variables)

    assert Berth.objects.count() == 1
    assert BerthType.objects.count() == 2

    assert executed["data"]["updateBerth"]["berth"] == {
        "id": global_id,
        "comment": berth.comment,
        "number": berth.number,
        "isAccessible": berth.is_accessible,
        "pier": {"id": to_global_id(PierNode._meta.name, berth.pier.id)},
        "isActive": berth.is_active,
        "width": variables["width"],
        "length": variables["length"],
        "depth": variables["depth"],
        "mooringType": variables["mooringType"],
        "isInvoiceable": berth.is_invoiceable,
    }


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_update_berth_to_non_invoiceable(berth, pier, api_client):
    global_id = to_global_id(BerthNode._meta.name, str(berth.id))

    variables = {
        "id": global_id,
        "isInvoiceable": False,
    }

    executed = api_client.execute(UPDATE_BERTH_MUTATION, input=variables)

    assert executed["data"]["updateBerth"]["berth"] == {
        "id": global_id,
        "comment": berth.comment,
        "number": berth.number,
        "isAccessible": berth.is_accessible,
        "pier": {"id": to_global_id(PierNode._meta.name, berth.pier.id)},
        "isActive": berth.is_active,
        "width": float(berth.berth_type.width),
        "length": float(berth.berth_type.length),
        "depth": float(berth.berth_type.depth),
        "mooringType": berth.berth_type.mooring_type.name,
        "isInvoiceable": False,
    }


def test_update_berth_no_id(berth, pier, berth_type, superuser_api_client):
    pier_id = to_global_id(PierNode._meta.name, str(pier.id))

    variables = {
        "number": "666",
        "comment": "foobar",
        "pierId": pier_id,
    }

    assert Berth.objects.count() == 1

    executed = superuser_api_client.execute(UPDATE_BERTH_MUTATION, input=variables)

    assert Berth.objects.count() == 1
    assert_field_missing("id", executed)


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_update_berth_not_enough_permissions(api_client, berth, pier, berth_type):
    pier_id = to_global_id(PierNode._meta.name, str(pier.id))

    variables = {
        "id": to_global_id(BerthNode._meta.name, str(berth.id)),
        "number": "666",
        "comment": "foobar",
        "pierId": pier_id,
        "width": round(random.uniform(1.5, 99.0), 2),
        "length": round(random.uniform(1.5, 99.0), 2),
        "depth": round(random.uniform(1.5, 99.0), 2),
        "mooringType": random.choice(list(BerthMooringType)).name,
    }
    assert Berth.objects.count() == 1

    executed = api_client.execute(UPDATE_BERTH_MUTATION, input=variables)

    assert Berth.objects.count() == 1
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
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_create_harbor(api_client, availability_level, municipality):
    variables = {
        "availabilityLevelId": availability_level.id,
        "municipalityId": municipality.id,
        "name": "Foobarsatama",
        "streetAddress": "Foobarstatmanrantatie 1234",
        "servicemapId": "1",
        "zipCode": "00100",
        "location": {"type": "Point", "coordinates": [66.6, 99.9]},
    }

    assert Harbor.objects.count() == 0

    executed = api_client.execute(CREATE_HARBOR_MUTATION, input=variables)

    assert Harbor.objects.count() == 1

    harbor_id = from_global_id(executed["data"]["createHarbor"]["harbor"].pop("id"))[1]

    assert harbor_id is not None
    assert executed["data"]["createHarbor"]["harbor"]["geometry"] == {
        "type": variables["location"]["type"],
        "coordinates": variables["location"]["coordinates"],
    }
    assert executed["data"]["createHarbor"]["harbor"]["bbox"] == (
        variables["location"]["coordinates"][0],
        variables["location"]["coordinates"][1],
        variables["location"]["coordinates"][0],
        variables["location"]["coordinates"][1],
    )
    assert executed["data"]["createHarbor"]["harbor"]["properties"] == {
        "name": variables["name"],
        "servicemapId": variables["servicemapId"],
        "streetAddress": variables["streetAddress"],
        "zipCode": variables["zipCode"],
        "availabilityLevel": {"id": str(availability_level.id)},
        "municipality": municipality.name,
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_create_harbor_not_enough_permissions(api_client):
    variables = {"name": "Foobarsatama"}

    assert Harbor.objects.count() == 0

    executed = api_client.execute(CREATE_HARBOR_MUTATION, input=variables)

    assert Harbor.objects.count() == 0
    assert_not_enough_permissions(executed)


def test_create_harbor_availability_level_doesnt_exist(superuser_api_client):
    variables = {"availabilityLevelId": "9999"}

    assert Harbor.objects.count() == 0

    executed = superuser_api_client.execute(CREATE_HARBOR_MUTATION, input=variables)

    assert Harbor.objects.count() == 0
    assert_doesnt_exist("AvailabilityLevel", executed)


def test_create_harbor_municipality_doesnt_exist(superuser_api_client):
    variables = {"municipalityId": "foobarland"}

    assert Harbor.objects.count() == 0

    executed = superuser_api_client.execute(CREATE_HARBOR_MUTATION, input=variables)

    assert Harbor.objects.count() == 0
    assert_doesnt_exist("Municipality", executed)


def test_create_harbor_duplicated_servicemap_id(superuser_api_client, harbor):
    variables = {"servicemapId": str(harbor.servicemap_id)}

    assert Harbor.objects.count() == 1

    executed = superuser_api_client.execute(CREATE_HARBOR_MUTATION, input=variables)

    assert Harbor.objects.count() == 1
    assert_field_duplicated("servicemap_id", executed)


DELETE_HARBOR_MUTATION = """
mutation DeleteHarbor($input: DeleteHarborMutationInput!) {
    deleteHarbor(input: $input) {
        __typename
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_delete_harbor(api_client, harbor):
    variables = {
        "id": to_global_id(HarborNode._meta.name, str(harbor.id)),
    }

    assert Harbor.objects.count() == 1

    api_client.execute(DELETE_HARBOR_MUTATION, input=variables)

    assert Harbor.objects.count() == 0


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_delete_harbor_not_enough_permissions(api_client, harbor):
    variables = {
        "id": to_global_id(HarborNode._meta.name, str(harbor.id)),
    }

    assert Harbor.objects.count() == 1

    executed = api_client.execute(DELETE_HARBOR_MUTATION, input=variables)

    assert Harbor.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_delete_harbor_inexistent_harbor(superuser_api_client):
    variables = {
        "id": to_global_id(HarborNode._meta.name, uuid.uuid4()),
    }

    executed = superuser_api_client.execute(DELETE_HARBOR_MUTATION, input=variables)

    assert_doesnt_exist("Harbor", executed)


def test_delete_harbor_with_lease(superuser_api_client, berth):
    berth_lease = BerthLeaseFactory(berth=berth, status=LeaseStatus.DRAFTED)
    variables = {
        "id": to_global_id(HarborNode._meta.name, berth_lease.berth.pier.harbor.id),
    }

    assert Harbor.objects.count() == 1

    superuser_api_client.execute(DELETE_HARBOR_MUTATION, input=variables)

    assert Harbor.objects.count() == 0


def test_delete_harbor_protected_with_lease(superuser_api_client, berth):
    berth_lease = BerthLeaseFactory(berth=berth, status=LeaseStatus.PAID)
    variables = {
        "id": to_global_id(HarborNode._meta.name, berth_lease.berth.pier.harbor.id),
    }

    executed = superuser_api_client.execute(DELETE_HARBOR_MUTATION, input=variables)

    assert_in_errors(
        "Cannot delete Harbor because it has some related leases", executed,
    )


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
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_update_harbor(api_client, harbor, availability_level, municipality):
    global_id = to_global_id(HarborNode._meta.name, str(harbor.id))

    variables = {
        "id": global_id,
        "availabilityLevelId": availability_level.id,
        "municipalityId": municipality.id,
        "name": "Uusi Foobarsatama",
        "streetAddress": "Uusifoobarstatmanrantatie 2345",
        "servicemapId": "1",
        "zipCode": "10101",
        "location": {"type": "Point", "coordinates": [99.9, 66.6]},
    }

    assert Harbor.objects.count() == 1

    executed = api_client.execute(UPDATE_HARBOR_MUTATION, input=variables)

    assert Harbor.objects.count() == 1
    assert executed["data"]["updateHarbor"]["harbor"]["id"] == global_id
    assert executed["data"]["updateHarbor"]["harbor"]["geometry"] == {
        "type": variables["location"]["type"],
        "coordinates": variables["location"]["coordinates"],
    }
    assert executed["data"]["updateHarbor"]["harbor"]["bbox"] == (
        variables["location"]["coordinates"][0],
        variables["location"]["coordinates"][1],
        variables["location"]["coordinates"][0],
        variables["location"]["coordinates"][1],
    )

    assert executed["data"]["updateHarbor"]["harbor"]["properties"] == {
        "name": variables["name"],
        "servicemapId": variables["servicemapId"],
        "streetAddress": variables["streetAddress"],
        "zipCode": variables["zipCode"],
        "availabilityLevel": {"id": str(availability_level.id)},
        "municipality": municipality.name,
    }


# Handling map files is disabled
#
# @pytest.mark.parametrize(
#     "api_client", ["harbor_services", "berth_services"], indirect=True,
# )
# def test_update_harbor_remove_map(api_client, harbor):
#     global_id = to_global_id(HarborNode._meta.name, str(harbor.id))
#     map_file_names = ["map1.pdf", "map2.pdf", "map3.pdf"]
#
#     # Create map objects and get only the IDs
#     map_files = [
#         HarborMap.objects.create(
#             map_file=SimpleUploadedFile(
#                 name=file_name, content=None, content_type="application/pdf"
#             ),
#             harbor=harbor,
#         ).id
#         for file_name in map_file_names
#     ]
#
#     assert harbor.maps.count() == 3
#
#     variables = {"id": global_id, "removeMapFiles": map_files}
#
#     executed = api_client.execute(UPDATE_HARBOR_MUTATION, input=variables)
#
#     assert len(executed["data"]["updateHarbor"]["harbor"]["properties"]["maps"]) == 0


def test_update_harbor_no_id(superuser_api_client, harbor):
    variables = {"name": "Uusi Foobarsatama"}

    assert Harbor.objects.count() == 1

    executed = superuser_api_client.execute(UPDATE_HARBOR_MUTATION, input=variables)

    assert Harbor.objects.count() == 1
    assert_field_missing("id", executed)


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_update_harbor_not_enough_permissions(api_client, harbor):
    variables = {
        "id": to_global_id(HarborNode._meta.name, str(harbor.id)),
    }
    assert Harbor.objects.count() == 1

    executed = api_client.execute(UPDATE_HARBOR_MUTATION, input=variables)

    assert Harbor.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_update_harbor_availability_level_doesnt_exist(harbor, superuser_api_client):
    variables = {
        "id": to_global_id(HarborNode._meta.name, harbor.id),
        "availabilityLevelId": "9999",
    }

    assert Harbor.objects.count() == 1

    executed = superuser_api_client.execute(UPDATE_HARBOR_MUTATION, input=variables)

    assert Harbor.objects.count() == 1
    assert_doesnt_exist("AvailabilityLevel", executed)


def test_update_harbor_municipality_doesnt_exist(harbor, superuser_api_client):
    variables = {
        "id": to_global_id(HarborNode._meta.name, harbor.id),
        "municipalityId": "foobarland",
    }

    assert Harbor.objects.count() == 1

    executed = superuser_api_client.execute(UPDATE_HARBOR_MUTATION, input=variables)

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
                priceTier
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_create_pier(api_client, harbor, boat_type):
    harbor_id = to_global_id(HarborNode._meta.name, harbor.id)
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
        "priceTier": PriceTier.TIER_1.name,
    }
    assert Pier.objects.count() == 0

    executed = api_client.execute(CREATE_PIER_MUTATION, input=variables)

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
        "priceTier": PriceTier.TIER_1.name,
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_create_pier_not_enough_permissions(api_client):
    variables = {"harborId": "", "priceTier": PriceTier.TIER_1.name}

    assert Pier.objects.count() == 0

    executed = api_client.execute(CREATE_PIER_MUTATION, input=variables)

    assert Pier.objects.count() == 0
    assert_not_enough_permissions(executed)


def test_create_pier_harbor_doesnt_exist(superuser_api_client):
    variables = {
        "harborId": to_global_id(HarborNode._meta.name, uuid.uuid4()),
        "priceTier": PriceTier.TIER_1.name,
    }

    assert Pier.objects.count() == 0

    executed = superuser_api_client.execute(CREATE_PIER_MUTATION, input=variables)

    assert Pier.objects.count() == 0
    assert_doesnt_exist("Harbor", executed)


def test_create_pier_no_harbor(superuser_api_client):
    variables = {"identifier": "foo"}

    assert Pier.objects.count() == 0

    executed = superuser_api_client.execute(CREATE_PIER_MUTATION, input=variables)

    assert Pier.objects.count() == 0
    assert_field_missing("harborId", executed)


DELETE_PIER_MUTATION = """
mutation DeletePier($input: DeletePierMutationInput!) {
    deletePier(input: $input) {
        __typename
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_delete_pier(api_client, pier):
    variables = {"id": to_global_id(PierNode._meta.name, str(pier.id))}

    assert Pier.objects.count() == 1

    api_client.execute(
        DELETE_PIER_MUTATION, input=variables,
    )

    assert Pier.objects.count() == 0


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_delete_pier_not_enough_permissions(api_client, pier):
    variables = {"id": to_global_id(PierNode._meta.name, str(pier.id))}

    assert Pier.objects.count() == 1

    executed = api_client.execute(DELETE_PIER_MUTATION, input=variables)

    assert Pier.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_delete_pier_inexistent_pier(superuser_api_client):
    variables = {"id": to_global_id(PierNode._meta.name, uuid.uuid4())}

    executed = superuser_api_client.execute(DELETE_PIER_MUTATION, input=variables)

    assert_doesnt_exist("Pier", executed)


def test_delete_pier_with_lease(superuser_api_client, berth):
    berth_lease = BerthLeaseFactory(berth=berth, status=LeaseStatus.DRAFTED)
    variables = {
        "id": to_global_id(PierNode._meta.name, berth_lease.berth.pier.id),
    }

    assert Pier.objects.count() == 1

    superuser_api_client.execute(DELETE_PIER_MUTATION, input=variables)

    assert Pier.objects.count() == 0


def test_delete_pier_protected_with_lease(superuser_api_client, berth):
    berth_lease = BerthLeaseFactory(berth=berth, status=LeaseStatus.PAID)
    variables = {
        "id": to_global_id(PierNode._meta.name, berth_lease.berth.pier.id),
    }

    executed = superuser_api_client.execute(DELETE_PIER_MUTATION, input=variables)

    assert_in_errors(
        "Cannot delete Pier because it has some related leases", executed,
    )


UPDATE_PIER_MUTATION = """
mutation UpdatePier($input: UpdatePierMutationInput!) {
    updatePier(input: $input) {
        pier {
            id
            geometry {
                type
                coordinates
            }
            bbox
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


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_update_pier(api_client, pier, harbor, boat_type):
    global_id = to_global_id(PierNode._meta.name, str(pier.id))
    harbor_id = to_global_id(HarborNode._meta.name, str(harbor.id))
    boat_types = [boat_type.id]

    variables = {
        "id": global_id,
        "harborId": harbor_id,
        "lighting": False,
        "wasteCollection": False,
        "mooring": False,
        "suitableBoatTypes": boat_types,
        "identifier": "foobar",
        "location": {"type": "Point", "coordinates": [66.6, 99.9]},
        "water": False,
        "electricity": False,
        "gate": False,
    }

    assert Pier.objects.count() == 1

    executed = api_client.execute(UPDATE_PIER_MUTATION, input=variables)

    assert Pier.objects.count() == 1
    assert executed["data"]["updatePier"]["pier"]["id"] == global_id
    assert executed["data"]["updatePier"]["pier"]["geometry"] == {
        "type": variables["location"]["type"],
        "coordinates": variables["location"]["coordinates"],
    }
    assert executed["data"]["updatePier"]["pier"]["bbox"] == (
        variables["location"]["coordinates"][0],
        variables["location"]["coordinates"][1],
        variables["location"]["coordinates"][0],
        variables["location"]["coordinates"][1],
    )
    assert executed["data"]["updatePier"]["pier"]["properties"] == {
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


def test_update_pier_no_id(superuser_api_client, pier):
    variables = {"water": False}

    assert Pier.objects.count() == 1

    executed = superuser_api_client.execute(UPDATE_PIER_MUTATION, input=variables)

    assert Pier.objects.count() == 1
    assert_field_missing("id", executed)


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_update_pier_not_enough_permissions(api_client, pier):
    variables = {"id": to_global_id(PierNode._meta.name, str(pier.id))}
    assert Pier.objects.count() == 1

    executed = api_client.execute(UPDATE_PIER_MUTATION, input=variables)

    assert Pier.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_update_pier_empty_boat_type_list(superuser_api_client, pier):
    global_id = to_global_id(PierNode._meta.name, pier.id)
    variables = {"id": global_id, "suitableBoatTypes": []}

    assert Pier.objects.count() == 1

    executed = superuser_api_client.execute(UPDATE_PIER_MUTATION, input=variables)

    assert Pier.objects.count() == 1
    assert executed["data"]["updatePier"]["pier"]["id"] == global_id
    assert (
        len(executed["data"]["updatePier"]["pier"]["properties"]["suitableBoatTypes"])
        == 0
    )


def test_update_pier_harbor_doesnt_exist(superuser_api_client, pier):
    variables = {
        "id": to_global_id(PierNode._meta.name, pier.id),
        "harborId": to_global_id(HarborNode._meta.name, uuid.uuid4()),
    }

    assert Pier.objects.count() == 1

    executed = superuser_api_client.execute(UPDATE_PIER_MUTATION, input=variables)

    assert Pier.objects.count() == 1
    assert_doesnt_exist("Harbor", executed)


CREATE_WINTER_STORAGE_AREA_MUTATION = """
mutation CreateWinterStorageArea($input: CreateWinterStorageAreaMutationInput!) {
    createWinterStorageArea(input: $input) {
        winterStorageArea {
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
                estimatedNumberOfUnmarkedSpaces
                maxLengthOfSectionSpaces
                estimatedNumberOfSectionSpaces
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_create_winter_storage_area(pier, api_client, availability_level, municipality):
    variables = {
        "availabilityLevelId": availability_level.id,  # why not use to_global_id here?
        "municipalityId": municipality.id,
        "estimatedNumberOfSectionSpaces": 50,
        "maxLengthOfSectionSpaces": decimal.Decimal("6.5"),
        "estimatedNumberOfUnmarkedSpaces": 10,
        "name": "area 52",
        "streetAddress": "Foobarstatmanrantatie 1234",
        "servicemapId": "1",
        "zipCode": "00100",
        "location": {"type": "Point", "coordinates": [66.6, 99.9]},
    }

    assert WinterStorageArea.objects.count() == 0

    executed = api_client.execute(CREATE_WINTER_STORAGE_AREA_MUTATION, input=variables)
    assert WinterStorageArea.objects.count() == 1
    area_id = from_global_id(
        executed["data"]["createWinterStorageArea"]["winterStorageArea"].pop("id")
    )[1]

    assert area_id is not None

    assert executed["data"]["createWinterStorageArea"]["winterStorageArea"][
        "geometry"
    ] == {
        "type": variables["location"]["type"],
        "coordinates": variables["location"]["coordinates"],
    }
    # bbox comes from GeoJSON
    assert executed["data"]["createWinterStorageArea"]["winterStorageArea"]["bbox"] == (
        variables["location"]["coordinates"][0],
        variables["location"]["coordinates"][1],
        variables["location"]["coordinates"][0],
        variables["location"]["coordinates"][1],
    )
    assert executed["data"]["createWinterStorageArea"]["winterStorageArea"][
        "properties"
    ] == {
        "name": variables["name"],
        "servicemapId": variables["servicemapId"],
        "streetAddress": variables["streetAddress"],
        "zipCode": variables["zipCode"],
        "availabilityLevel": {"id": str(availability_level.id)},
        "estimatedNumberOfSectionSpaces": variables["estimatedNumberOfSectionSpaces"],
        "maxLengthOfSectionSpaces": str(variables["maxLengthOfSectionSpaces"]),
        "estimatedNumberOfUnmarkedSpaces": variables["estimatedNumberOfUnmarkedSpaces"],
        "municipality": municipality.name,
    }


DELETE_WINTER_STORAGE_AREA_MUTATION = """
mutation DeleteWinterStorageArea($input: DeleteWinterStorageAreaMutationInput!) {
    deleteWinterStorageArea(input: $input) {
        __typename
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_delete_winter_storage_area(api_client, winter_storage_area):
    variables = {
        "id": to_global_id(
            WinterStorageAreaNode._meta.name, str(winter_storage_area.id)
        ),
    }

    assert WinterStorageArea.objects.count() == 1

    api_client.execute(DELETE_WINTER_STORAGE_AREA_MUTATION, input=variables)

    assert WinterStorageArea.objects.count() == 0


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_delete_winter_storage_area_not_enough_permissions(
    api_client, winter_storage_area
):
    variables = {
        "id": to_global_id(
            WinterStorageAreaNode._meta.name, str(winter_storage_area.id)
        ),
    }

    assert WinterStorageArea.objects.count() == 1

    executed = api_client.execute(DELETE_WINTER_STORAGE_AREA_MUTATION, input=variables)

    assert WinterStorageArea.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_delete_winter_storage_area_inexistent_winter_storage_area(
    superuser_api_client,
):
    variables = {
        "id": to_global_id(WinterStorageAreaNode._meta.name, uuid.uuid4()),
    }

    executed = superuser_api_client.execute(
        DELETE_WINTER_STORAGE_AREA_MUTATION, input=variables
    )
    assert_doesnt_exist("WinterStorageArea", executed)


def test_delete_winter_storage_area_with_lease_at_place(
    superuser_api_client, winter_storage_place
):
    """
    WinterStorageLease can be associated with a WinterStorageArea either through a WinterStoragePlace,
    or directly through WinterStorageSection.
    """
    winter_storage_lease = WinterStorageLeaseFactory(
        place=winter_storage_place, status=LeaseStatus.DRAFTED
    )
    variables = {
        "id": to_global_id(
            WinterStorageAreaNode._meta.name,
            winter_storage_lease.place.winter_storage_section.area.id,
        ),
    }

    assert WinterStorageArea.objects.count() == 1

    superuser_api_client.execute(DELETE_WINTER_STORAGE_AREA_MUTATION, input=variables)

    assert WinterStorageArea.objects.count() == 0


def test_delete_winter_storage_area_with_lease_at_section(
    superuser_api_client, winter_storage_section
):
    winter_storage_lease = WinterStorageLeaseFactory(
        section=winter_storage_section, place=None, status=LeaseStatus.DRAFTED
    )
    variables = {
        "id": to_global_id(
            WinterStorageAreaNode._meta.name, winter_storage_lease.section.area.id
        ),
    }

    assert WinterStorageArea.objects.count() == 1

    superuser_api_client.execute(DELETE_WINTER_STORAGE_AREA_MUTATION, input=variables)

    assert WinterStorageArea.objects.count() == 0


def test_delete_winter_storage_area_protected_with_lease_at_place(
    superuser_api_client, winter_storage_place
):
    winter_storage_lease = WinterStorageLeaseFactory(
        place=winter_storage_place, status=LeaseStatus.PAID
    )
    variables = {
        "id": to_global_id(
            WinterStorageAreaNode._meta.name,
            winter_storage_lease.place.winter_storage_section.area.id,
        ),
    }

    executed = superuser_api_client.execute(
        DELETE_WINTER_STORAGE_AREA_MUTATION, input=variables
    )

    assert_in_errors(
        "Cannot delete WinterStorageArea because it has some related leases", executed,
    )


def test_delete_winter_storage_area_protected_with_lease_at_section(
    superuser_api_client, winter_storage_section
):
    winter_storage_lease = WinterStorageLeaseFactory(
        section=winter_storage_section, place=None, status=LeaseStatus.PAID
    )
    variables = {
        "id": to_global_id(
            WinterStorageAreaNode._meta.name, winter_storage_lease.section.area.id
        ),
    }

    executed = superuser_api_client.execute(
        DELETE_WINTER_STORAGE_AREA_MUTATION, input=variables
    )

    assert_in_errors(
        "Cannot delete WinterStorageArea because it has some related leases", executed,
    )


CREATE_WINTER_STORAGE_PLACE_TYPE_MUTATION = """
mutation CreateWinterStoragePlaceType($input: CreateWinterStoragePlaceTypeMutationInput!) {
    createWinterStoragePlaceType(input: $input) {
        winterStoragePlaceType {
            id
            width
            length
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_create_winter_storage_place_type(api_client):
    variables = {
        "width": decimal.Decimal("1.5"),
        "length": decimal.Decimal("5.5"),
    }

    assert WinterStoragePlaceType.objects.count() == 0

    executed = api_client.execute(
        CREATE_WINTER_STORAGE_PLACE_TYPE_MUTATION, input=variables
    )

    assert WinterStoragePlaceType.objects.count() == 1
    # Check that no more winterStoragePlaceType types were created
    assert WinterStoragePlaceType.objects.count() == 1
    assert (
        executed["data"]["createWinterStoragePlaceType"]["winterStoragePlaceType"].pop(
            "id"
        )
        is not None
    )

    assert executed["data"]["createWinterStoragePlaceType"][
        "winterStoragePlaceType"
    ] == {"width": variables["width"], "length": variables["length"]}


DELETE_WINTER_STORAGE_PLACE_TYPE_MUTATION = """
mutation DeleteWinterStoragePlaceType($input: DeleteWinterStoragePlaceTypeMutationInput!) {
    deleteWinterStoragePlaceType(input: $input) {
        __typename
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_delete_winter_storage_place_type(api_client, winter_storage_place_type):
    variables = {
        "id": to_global_id(
            WinterStoragePlaceTypeNode._meta.name, str(winter_storage_place_type.id)
        ),
    }

    assert WinterStoragePlaceType.objects.count() == 1

    api_client.execute(DELETE_WINTER_STORAGE_PLACE_TYPE_MUTATION, input=variables)

    assert WinterStoragePlaceType.objects.count() == 0


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_delete_winter_storage_place_type_not_enough_permissions(
    api_client, winter_storage_place_type
):
    variables = {
        "id": to_global_id(
            WinterStoragePlaceTypeNode._meta.name, str(winter_storage_place_type.id)
        ),
    }

    assert WinterStoragePlaceType.objects.count() == 1

    executed = api_client.execute(
        DELETE_WINTER_STORAGE_PLACE_TYPE_MUTATION, input=variables
    )

    assert WinterStoragePlaceType.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_delete_winter_storage_place_type_nonexistent_object(superuser_api_client):
    variables = {
        "id": to_global_id(WinterStoragePlaceTypeNode._meta.name, uuid.uuid4()),
    }

    executed = superuser_api_client.execute(
        DELETE_WINTER_STORAGE_PLACE_TYPE_MUTATION, input=variables
    )

    assert_doesnt_exist("WinterStoragePlaceType", executed)


def test_delete_winter_storage_place_type_protected_with_places(
    superuser_api_client, winter_storage_place_type
):
    place = WinterStoragePlaceFactory(place_type=winter_storage_place_type)
    variables = {
        "id": to_global_id(WinterStoragePlaceTypeNode._meta.name, place.place_type.id),
    }

    executed = superuser_api_client.execute(
        DELETE_WINTER_STORAGE_PLACE_TYPE_MUTATION, input=variables
    )
    assert_in_errors(
        "Cannot delete WinterStoragePlaceType because it has 1 related places",
        executed,
    )


UPDATE_WINTER_STORAGE_PLACE_TYPE_MUTATION = """
mutation UpdateWinterStoragePlaceType($input: UpdateWinterStoragePlaceTypeMutationInput!) {
    updateWinterStoragePlaceType(input: $input) {
        winterStoragePlaceType {
            id
            width
            length
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_update_winter_storage_place_type(api_client, winter_storage_place_type):
    global_id = to_global_id(
        WinterStoragePlaceTypeNode._meta.name, str(winter_storage_place_type.id)
    )

    variables = {
        "id": global_id,
        "width": "3.3",
        "length": "4.4",
    }

    assert WinterStoragePlaceType.objects.count() == 1

    executed = api_client.execute(
        UPDATE_WINTER_STORAGE_PLACE_TYPE_MUTATION, input=variables
    )

    assert "data" in executed
    assert WinterStoragePlaceType.objects.count() == 1
    assert executed["data"]["updateWinterStoragePlaceType"][
        "winterStoragePlaceType"
    ] == {"id": global_id, "width": 3.3, "length": 4.4}


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_update_winter_storage_place_type_not_enough_permissions(
    api_client, winter_storage_place_type
):

    variables = {
        "id": to_global_id(
            WinterStoragePlaceTypeNode._meta.name, str(winter_storage_place_type.id)
        ),
        "width": round(random.uniform(1.5, 99.0), 2),
        "length": round(random.uniform(1.5, 99.0), 2),
    }
    assert WinterStoragePlaceType.objects.count() == 1

    executed = api_client.execute(
        UPDATE_WINTER_STORAGE_PLACE_TYPE_MUTATION, input=variables
    )

    assert WinterStoragePlaceType.objects.count() == 1
    assert_not_enough_permissions(executed)


CREATE_WINTER_STORAGE_SECTION_MUTATION = """
mutation CreateWinterStorageSection($input: CreateWinterStorageSectionMutationInput!) {
    createWinterStorageSection(input: $input) {
        winterStorageSection {
            id
            bbox
            geometry {
                type
                coordinates
            }
            properties {
                area {
                    id
                }
                identifier
                electricity
                water
                gate
                summerStorageForDockingEquipment
                summerStorageForTrailers
                summerStorageForBoats
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_create_winter_storage_section_plain(api_client, winter_storage_area):
    winter_storage_area_id = to_global_id(
        WinterStorageAreaNode._meta.name, winter_storage_area.id
    )

    variables = {
        "areaId": winter_storage_area_id,
        "identifier": "foobar",
        "location": {"type": "Point", "coordinates": [66.6, 77.7]},
        "electricity": True,
        "water": True,
        "gate": True,
        "summerStorageForDockingEquipment": True,
        "summerStorageForTrailers": True,
        "summerStorageForBoats": True,
    }
    assert WinterStorageSection.objects.count() == 0

    executed = api_client.execute(
        CREATE_WINTER_STORAGE_SECTION_MUTATION, input=variables
    )

    assert "data" in executed
    assert WinterStorageSection.objects.count() == 1
    assert (
        executed["data"]["createWinterStorageSection"]["winterStorageSection"]["id"]
        is not None
    )

    assert executed["data"]["createWinterStorageSection"]["winterStorageSection"][
        "geometry"
    ] == {
        "type": variables["location"]["type"],
        "coordinates": variables["location"]["coordinates"],
    }
    assert executed["data"]["createWinterStorageSection"]["winterStorageSection"][
        "bbox"
    ] == (
        variables["location"]["coordinates"][0],
        variables["location"]["coordinates"][1],
        variables["location"]["coordinates"][0],
        variables["location"]["coordinates"][1],
    )

    assert executed["data"]["createWinterStorageSection"]["winterStorageSection"][
        "properties"
    ] == {
        "area": {"id": winter_storage_area_id},
        "identifier": variables["identifier"],
        "electricity": variables["electricity"],
        "gate": variables["gate"],
        "water": variables["water"],
        "summerStorageForDockingEquipment": variables[
            "summerStorageForDockingEquipment"
        ],
        "summerStorageForTrailers": variables["summerStorageForTrailers"],
        "summerStorageForBoats": variables["summerStorageForBoats"],
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_create_winter_storage_section_not_enough_permissions(api_client):
    variables = {"areaId": ""}

    assert WinterStorageSection.objects.count() == 0

    executed = api_client.execute(
        CREATE_WINTER_STORAGE_SECTION_MUTATION, input=variables
    )

    assert WinterStorageSection.objects.count() == 0
    assert_not_enough_permissions(executed)


def test_create_winter_storage_section_winter_storage_area_doesnt_exist(
    superuser_api_client,
):
    variables = {"areaId": to_global_id(WinterStorageAreaNode._meta.name, uuid.uuid4())}

    assert WinterStorageSection.objects.count() == 0

    executed = superuser_api_client.execute(
        CREATE_WINTER_STORAGE_SECTION_MUTATION, input=variables
    )

    assert WinterStorageSection.objects.count() == 0

    assert_doesnt_exist("WinterStorageArea", executed)


def test_create_winter_storage_section_no_winter_storage_area(superuser_api_client):
    variables = {"identifier": "foo"}

    assert WinterStorageSection.objects.count() == 0

    executed = superuser_api_client.execute(
        CREATE_WINTER_STORAGE_SECTION_MUTATION, input=variables
    )

    assert WinterStorageSection.objects.count() == 0
    assert_field_missing("area", executed)


DELETE_WINTER_STORAGE_SECTION_MUTATION = """
mutation DeleteWinterStorageSection($input: DeleteWinterStorageSectionMutationInput!) {
    deleteWinterStorageSection(input: $input) {
        __typename
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_delete_winter_storage_section(api_client, winter_storage_section):
    variables = {
        "id": to_global_id(
            WinterStorageSectionNode._meta.name, str(winter_storage_section.id)
        )
    }

    assert WinterStorageSection.objects.count() == 1

    api_client.execute(
        DELETE_WINTER_STORAGE_SECTION_MUTATION, input=variables,
    )

    assert WinterStorageSection.objects.count() == 0


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_delete_winter_storage_section_not_enough_permissions(
    api_client, winter_storage_section
):
    variables = {
        "id": to_global_id(
            WinterStorageSectionNode._meta.name, str(winter_storage_section.id)
        )
    }

    assert WinterStorageSection.objects.count() == 1

    executed = api_client.execute(
        DELETE_WINTER_STORAGE_SECTION_MUTATION, input=variables
    )

    assert WinterStorageSection.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_delete_winter_storage_section_nonexistent(superuser_api_client):
    variables = {"id": to_global_id(WinterStorageSectionNode._meta.name, uuid.uuid4())}

    executed = superuser_api_client.execute(
        DELETE_WINTER_STORAGE_SECTION_MUTATION, input=variables
    )

    assert_doesnt_exist("WinterStorageSection", executed)


def test_delete_winter_storage_section_with_lease(
    superuser_api_client, winter_storage_place
):
    winter_storage_lease = WinterStorageLeaseFactory(
        place=winter_storage_place, status=LeaseStatus.DRAFTED
    )

    variables = {
        "id": to_global_id(
            WinterStorageSectionNode._meta.name,
            winter_storage_lease.place.winter_storage_section.id,
        ),
    }

    assert WinterStorageSection.objects.count() == 1

    superuser_api_client.execute(
        DELETE_WINTER_STORAGE_SECTION_MUTATION, input=variables
    )

    assert WinterStorageSection.objects.count() == 0


def test_delete_winter_storage_section_protected_with_lease(
    superuser_api_client, winter_storage_place
):
    winter_storage_lease = WinterStorageLeaseFactory(
        place=winter_storage_place, status=LeaseStatus.PAID
    )

    variables = {
        "id": to_global_id(
            WinterStorageSectionNode._meta.name,
            winter_storage_lease.place.winter_storage_section.id,
        ),
    }

    executed = superuser_api_client.execute(
        DELETE_WINTER_STORAGE_SECTION_MUTATION, input=variables
    )

    assert_in_errors(
        "Cannot delete WinterStorageSection because it has some related leases",
        executed,
    )


UPDATE_WINTER_STORAGE_SECTION_MUTATION = """
mutation UpdateWinterStorageSection($input: UpdateWinterStorageSectionMutationInput!) {
    updateWinterStorageSection(input: $input) {
        winterStorageSection {
            id
            geometry {
                type
                coordinates
            }
            bbox
            properties {
                area {
                    id
                }
                identifier
                electricity
                water
                gate
                summerStorageForDockingEquipment
                summerStorageForTrailers
                summerStorageForBoats
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_update_winter_storage_section(
    api_client, winter_storage_section, winter_storage_area, boat_type
):
    global_id = to_global_id(
        WinterStorageSectionNode._meta.name, str(winter_storage_section.id)
    )
    winter_storage_area_id = to_global_id(
        WinterStorageAreaNode._meta.name, str(winter_storage_area.id)
    )

    variables = {
        "id": global_id,
        "areaId": winter_storage_area_id,
        "identifier": "foobar",
        "location": {"type": "Point", "coordinates": [66.6, 77.7]},
        "electricity": True,
        "water": True,
        "gate": True,
        "summerStorageForDockingEquipment": True,
        "summerStorageForTrailers": True,
        "summerStorageForBoats": True,
    }

    assert WinterStorageSection.objects.count() == 1

    executed = api_client.execute(
        UPDATE_WINTER_STORAGE_SECTION_MUTATION, input=variables
    )
    assert WinterStorageSection.objects.count() == 1
    assert (
        executed["data"]["updateWinterStorageSection"]["winterStorageSection"]["id"]
        == global_id
    )
    assert executed["data"]["updateWinterStorageSection"]["winterStorageSection"][
        "geometry"
    ] == {
        "type": variables["location"]["type"],
        "coordinates": variables["location"]["coordinates"],
    }
    assert executed["data"]["updateWinterStorageSection"]["winterStorageSection"][
        "bbox"
    ] == (
        variables["location"]["coordinates"][0],
        variables["location"]["coordinates"][1],
        variables["location"]["coordinates"][0],
        variables["location"]["coordinates"][1],
    )
    assert executed["data"]["updateWinterStorageSection"]["winterStorageSection"][
        "properties"
    ] == {
        "area": {"id": winter_storage_area_id},
        "identifier": variables["identifier"],
        "electricity": variables["electricity"],
        "water": variables["water"],
        "gate": variables["gate"],
        "summerStorageForDockingEquipment": variables[
            "summerStorageForDockingEquipment"
        ],
        "summerStorageForTrailers": variables["summerStorageForTrailers"],
        "summerStorageForBoats": variables["summerStorageForBoats"],
    }


def test_update_winter_storage_section_no_id(
    superuser_api_client, winter_storage_section
):
    variables = {"water": False}

    assert WinterStorageSection.objects.count() == 1

    executed = superuser_api_client.execute(
        UPDATE_WINTER_STORAGE_SECTION_MUTATION, input=variables
    )

    assert WinterStorageSection.objects.count() == 1
    assert_field_missing("id", executed)


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_update_winter_storage_section_not_enough_permissions(
    api_client, winter_storage_section
):
    variables = {
        "id": to_global_id(
            WinterStorageSectionNode._meta.name, str(winter_storage_section.id)
        )
    }
    assert WinterStorageSection.objects.count() == 1

    executed = api_client.execute(
        UPDATE_WINTER_STORAGE_SECTION_MUTATION, input=variables
    )

    assert WinterStorageSection.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_update_winter_storage_section_winter_storage_area_doesnt_exist(
    superuser_api_client, winter_storage_section
):
    variables = {
        "id": to_global_id(
            WinterStorageSectionNode._meta.name, winter_storage_section.id
        ),
        "areaId": to_global_id(WinterStorageAreaNode._meta.name, uuid.uuid4()),
    }

    assert WinterStorageSection.objects.count() == 1

    executed = superuser_api_client.execute(
        UPDATE_WINTER_STORAGE_SECTION_MUTATION, input=variables
    )

    assert WinterStorageSection.objects.count() == 1
    assert_doesnt_exist("WinterStorageArea", executed)


CREATE_WINTER_STORAGE_PLACE_MUTATION = """
mutation CreateWinterStoragePlace($input: CreateWinterStoragePlaceMutationInput!) {
    createWinterStoragePlace(input: $input) {
        winterStoragePlace {
            id
            number
            isActive
            width
            length
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_create_winter_storage_place(
    winter_storage_section, api_client, winter_storage_place_type
):
    variables = {
        "number": 123,
        "winterStorageSectionId": to_global_id(
            WinterStorageSectionNode._meta.name, str(winter_storage_section.id)
        ),
        "isActive": False,
        "width": float(winter_storage_place_type.width),
        "length": float(winter_storage_place_type.length),
    }

    assert WinterStoragePlace.objects.count() == 0
    assert WinterStoragePlaceType.objects.count() == 1

    executed = api_client.execute(CREATE_WINTER_STORAGE_PLACE_MUTATION, input=variables)
    assert "data" in executed
    assert WinterStoragePlace.objects.count() == 1
    # Check that no more winter_storage_place types were created
    assert WinterStoragePlaceType.objects.count() == 1
    assert (
        executed["data"]["createWinterStoragePlace"]["winterStoragePlace"].pop("id")
        is not None
    )

    assert executed["data"]["createWinterStoragePlace"]["winterStoragePlace"] == {
        "number": 123,
        "isActive": False,
        "width": variables["width"],
        "length": variables["length"],
    }


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_create_winter_storage_place_new_winter_storage_place_type(
    winter_storage_section, api_client
):
    variables = {
        "number": 1234,
        "winterStorageSectionId": to_global_id(
            WinterStorageSectionNode._meta.name, str(winter_storage_section.id)
        ),
        "isActive": False,
        "width": round(random.uniform(1.5, 99.0), 2),
        "length": round(random.uniform(1.5, 99.0), 2),
    }

    assert WinterStoragePlace.objects.count() == 0
    assert WinterStoragePlaceType.objects.count() == 0

    executed = api_client.execute(CREATE_WINTER_STORAGE_PLACE_MUTATION, input=variables)

    assert WinterStoragePlace.objects.count() == 1
    assert WinterStoragePlaceType.objects.count() == 1

    assert (
        executed["data"]["createWinterStoragePlace"]["winterStoragePlace"].pop("id")
        is not None
    )

    assert executed["data"]["createWinterStoragePlace"]["winterStoragePlace"] == {
        "number": 1234,
        "isActive": False,
        "width": variables["width"],
        "length": variables["length"],
    }


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_create_winter_storage_place_not_enough_permissions(
    api_client, winter_storage_section, winter_storage_place_type
):
    variables = {
        "number": 213,
        "winterStorageSectionId": to_global_id(
            WinterStorageSectionNode._meta.name, str(winter_storage_section.id)
        ),
        "width": float(winter_storage_place_type.width),
        "length": float(winter_storage_place_type.length),
    }

    assert WinterStoragePlace.objects.count() == 0

    executed = api_client.execute(CREATE_WINTER_STORAGE_PLACE_MUTATION, input=variables)

    assert WinterStoragePlace.objects.count() == 0
    assert_not_enough_permissions(executed)


def test_create_winter_storage_place_no_number(
    winter_storage_section, superuser_api_client
):
    variables = {
        "winterStorageSectionId": to_global_id(
            WinterStorageSectionNode._meta.name, str(winter_storage_section.id)
        ),
    }

    assert WinterStoragePlace.objects.count() == 0

    executed = superuser_api_client.execute(
        CREATE_WINTER_STORAGE_PLACE_MUTATION, input=variables
    )

    assert WinterStoragePlace.objects.count() == 0
    assert_field_missing("number", executed)


DELETE_WINTER_STORAGE_PLACE_MUTATION = """
mutation DeleteWinterStoragePlace($input: DeleteWinterStoragePlaceMutationInput!) {
    deleteWinterStoragePlace(input: $input) {
        __typename
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_delete_winter_storage_place(api_client, winter_storage_place):
    variables = {
        "id": to_global_id(
            WinterStoragePlaceNode._meta.name, str(winter_storage_place.id)
        ),
    }

    assert WinterStoragePlace.objects.count() == 1

    api_client.execute(DELETE_WINTER_STORAGE_PLACE_MUTATION, input=variables)

    assert WinterStoragePlace.objects.count() == 0


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_delete_winter_storage_place_not_enough_permissions(
    api_client, winter_storage_place
):
    variables = {
        "id": to_global_id(
            WinterStoragePlaceNode._meta.name, str(winter_storage_place.id)
        ),
    }

    assert WinterStoragePlace.objects.count() == 1

    executed = api_client.execute(DELETE_WINTER_STORAGE_PLACE_MUTATION, input=variables)

    assert WinterStoragePlace.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_delete_winter_storage_place_inexistent_winter_storage_place(
    superuser_api_client,
):
    variables = {
        "id": to_global_id(WinterStoragePlaceNode._meta.name, uuid.uuid4()),
    }

    executed = superuser_api_client.execute(
        DELETE_WINTER_STORAGE_PLACE_MUTATION, input=variables
    )

    assert_doesnt_exist("WinterStoragePlace", executed)


def test_delete_winter_storage_place_with_lease(
    superuser_api_client, winter_storage_place
):
    winter_storage_place_lease = WinterStorageLeaseFactory(
        place=winter_storage_place, status=LeaseStatus.DRAFTED
    )
    variables = {
        "id": to_global_id(
            WinterStoragePlaceNode._meta.name, winter_storage_place_lease.place.id
        ),
    }

    assert WinterStoragePlace.objects.count() == 1

    superuser_api_client.execute(DELETE_WINTER_STORAGE_PLACE_MUTATION, input=variables)

    assert WinterStoragePlace.objects.count() == 0


def test_delete_winter_storage_place_protected_with_lease(
    superuser_api_client, winter_storage_place
):
    winter_storage_place_lease = WinterStorageLeaseFactory(
        place=winter_storage_place, status=LeaseStatus.PAID
    )
    variables = {
        "id": to_global_id(
            WinterStoragePlaceNode._meta.name, winter_storage_place_lease.place.id
        ),
    }

    executed = superuser_api_client.execute(
        DELETE_WINTER_STORAGE_PLACE_MUTATION, input=variables
    )

    assert_in_errors(
        "Cannot delete WinterStoragePlace because it has some related leases", executed,
    )


UPDATE_WINTER_STORAGE_PLACE_MUTATION = """
mutation UpdateWinterStoragePlace($input: UpdateWinterStoragePlaceMutationInput!) {
    updateWinterStoragePlace(input: $input) {
        winterStoragePlace {
            id
            number
            isActive
            winterStorageSection {
                id
            }
            width
            length
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_update_winter_storage_place(
    winter_storage_place, winter_storage_section, api_client
):
    global_id = to_global_id(
        WinterStoragePlaceNode._meta.name, str(winter_storage_place.id)
    )
    winter_storage_section_id = to_global_id(
        WinterStorageSectionNode._meta.name, str(winter_storage_section.id)
    )

    variables = {
        "id": global_id,
        "number": 123,
        "winterStorageSectionId": winter_storage_section_id,
        "isActive": False,
    }

    assert WinterStoragePlace.objects.count() == 1

    executed = api_client.execute(UPDATE_WINTER_STORAGE_PLACE_MUTATION, input=variables)

    assert WinterStoragePlace.objects.count() == 1
    assert executed["data"]["updateWinterStoragePlace"]["winterStoragePlace"] == {
        "id": global_id,
        "number": variables["number"],
        "winterStorageSection": {"id": variables["winterStorageSectionId"]},
        "isActive": variables["isActive"],
        "width": float(winter_storage_place.place_type.width),
        "length": float(winter_storage_place.place_type.length),
    }


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_update_winter_storage_place_existing_winter_storage_place_type(
    winter_storage_place, winter_storage_place_type, api_client
):
    global_id = to_global_id(
        WinterStoragePlaceNode._meta.name, str(winter_storage_place.id)
    )

    variables = {
        "id": global_id,
        "number": 111,
        "width": decimal.Decimal(winter_storage_place_type.width),
        "length": decimal.Decimal(winter_storage_place_type.length),
    }

    assert winter_storage_place.place_type != winter_storage_place_type
    assert WinterStoragePlace.objects.count() == 1
    assert WinterStoragePlaceType.objects.count() == 2

    executed = api_client.execute(UPDATE_WINTER_STORAGE_PLACE_MUTATION, input=variables)

    assert WinterStoragePlace.objects.count() == 1
    assert WinterStoragePlaceType.objects.count() == 2

    assert executed["data"]["updateWinterStoragePlace"]["winterStoragePlace"] == {
        "id": global_id,
        "number": variables["number"],
        "winterStorageSection": {
            "id": to_global_id(
                WinterStorageSectionNode._meta.name,
                winter_storage_place.winter_storage_section.id,
            )
        },
        "isActive": winter_storage_place.is_active,
        "width": float(winter_storage_place_type.width),
        "length": float(winter_storage_place_type.length),
    }
    assert (
        WinterStoragePlace.objects.get(id=winter_storage_place.id).place_type
        == winter_storage_place_type
    )


@pytest.mark.parametrize(
    "api_client", ["harbor_services", "berth_services"], indirect=True,
)
def test_update_winter_storage_place_new_place_type(winter_storage_place, api_client):
    global_id = to_global_id(
        WinterStoragePlaceNode._meta.name, str(winter_storage_place.id)
    )

    variables = {
        "id": global_id,
        "width": round(random.uniform(1.5, 99.0), 2),
        "length": round(random.uniform(1.5, 99.0), 2),
    }

    assert WinterStoragePlace.objects.count() == 1
    assert WinterStoragePlaceType.objects.count() == 1

    executed = api_client.execute(UPDATE_WINTER_STORAGE_PLACE_MUTATION, input=variables)

    assert WinterStoragePlace.objects.count() == 1
    assert WinterStoragePlaceType.objects.count() == 2

    assert executed["data"]["updateWinterStoragePlace"]["winterStoragePlace"] == {
        "id": global_id,
        "number": winter_storage_place.number,
        "winterStorageSection": {
            "id": to_global_id(
                WinterStorageSectionNode._meta.name,
                winter_storage_place.winter_storage_section.id,
            )
        },
        "isActive": winter_storage_place.is_active,
        "width": float(variables["width"]),
        "length": (variables["length"]),
    }


def test_update_winter_storage_place_no_id(
    winter_storage_place, winter_storage_section, superuser_api_client
):
    winter_storage_section_id = to_global_id(
        WinterStorageSectionNode._meta.name, str(winter_storage_section.id)
    )

    variables = {
        "number": 123,
        "winterStorageSectionId": winter_storage_section_id,
    }

    assert WinterStoragePlace.objects.count() == 1

    executed = superuser_api_client.execute(
        UPDATE_WINTER_STORAGE_PLACE_MUTATION, input=variables
    )

    assert WinterStoragePlace.objects.count() == 1
    assert_field_missing("id", executed)


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_update_winter_storage_place_not_enough_permissions(
    api_client, winter_storage_place, winter_storage_section
):
    winter_storage_section_id = to_global_id(
        WinterStorageSectionNode._meta.name, str(winter_storage_section.id)
    )

    variables = {
        "id": to_global_id(
            WinterStoragePlaceNode._meta.name, str(winter_storage_place.id)
        ),
        "number": 123,
        "winterStorageSectionId": winter_storage_section_id,
        "width": round(random.uniform(1.5, 99.0), 2),
        "length": round(random.uniform(1.5, 99.0), 2),
    }
    assert WinterStoragePlace.objects.count() == 1

    executed = api_client.execute(UPDATE_WINTER_STORAGE_PLACE_MUTATION, input=variables)

    assert WinterStoragePlace.objects.count() == 1
    assert_not_enough_permissions(executed)
