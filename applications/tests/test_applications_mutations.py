import random

import pytest
from django.core import mail

from berth_reservations.tests.factories import CustomerProfileFactory
from berth_reservations.tests.utils import (
    assert_doesnt_exist,
    assert_field_missing,
    assert_in_errors,
    assert_not_enough_permissions,
    create_api_client,
)
from customers.schema import BoatNode, ProfileNode
from customers.tests.factories import BoatFactory
from leases.tests.factories import BerthLeaseFactory
from resources.schema import BerthNode, HarborNode, WinterStorageAreaNode
from resources.tests.factories import (
    BerthFactory,
    BoatTypeFactory,
    WinterStorageAreaFactory,
    WinterStoragePlaceFactory,
)
from utils.relay import to_global_id

from ..enums import ApplicationPriority, ApplicationStatus
from ..models import BerthApplication, WinterStorageApplication
from ..schema import BerthApplicationNode
from ..schema.types import WinterStorageApplicationNode
from .factories import (
    BerthApplicationFactory,
    HarborChoiceFactory,
    WinterAreaChoiceFactory,
    WinterStorageApplicationFactory,
)

CREATE_BERTH_APPLICATION_MUTATION = """
mutation createBerthApplication($input: CreateBerthApplicationMutationInput!) {
    createBerthApplication(input: $input) {
        berthApplication {
            berthSwitch {
                berth {
                    id
                }
                reason {
                    id
                }
            }
            harborChoices {
                harbor {
                    id
                }
            }
            boatWidth
            boatLength
        }
    }
}
"""


@pytest.fixture
def berth():
    return BerthFactory()


@pytest.fixture
def create_berth_application_variables(berth_switch_reason, berth):
    berth_node_id = to_global_id(BerthNode, berth.id)
    harbor_node_id = to_global_id(HarborNode, berth.pier.harbor.id)

    return {
        "berthSwitch": {"berthId": berth_node_id, "reason": berth_switch_reason.id},
        "berthApplication": {
            "language": "en",
            "firstName": "John",
            "lastName": "Doe",
            "phoneNumber": "1234567890",
            "email": "john.doe@example.com",
            "address": "Mannerheimintie 1",
            "zipCode": "00100",
            "municipality": "Helsinki",
            "informationAccuracyConfirmed": True,
            "acceptFitnessNews": False,
            "acceptLibraryNews": False,
            "acceptOtherCultureNews": False,
            "acceptBoatingNewsletter": True,
            "choices": [{"harborId": harbor_node_id, "priority": 1}],
        },
    }


@pytest.fixture
def create_berth_application_result(berth_switch_reason, berth):
    berth_node_id = to_global_id(BerthNode, berth.id)
    harbor_node_id = to_global_id(HarborNode, berth.pier.harbor.id)

    return {
        "data": {
            "createBerthApplication": {
                "berthApplication": {
                    "berthSwitch": {
                        "berth": {"id": berth_node_id},
                        "reason": {"id": str(berth_switch_reason.id)},
                    },
                    "harborChoices": [{"harbor": {"id": harbor_node_id}}],
                    "boatLength": "2.00",
                    "boatWidth": "3.00",
                }
            }
        }
    }


def test_create_berth_application(
    superuser_api_client,
    create_berth_application_variables,
    create_berth_application_result,
):
    boat_type = BoatTypeFactory()
    create_berth_application_variables["berthApplication"].update(
        {
            "boatType": boat_type.id,
            "boatLength": "2.00",
            "boatWidth": "3.00",
            "boatRegistrationNumber": "U12345",
            "boatName": "Paatti",
            "boatModel": "xyz123",
            "boatDraught": "1.10",
            "boatWeight": "1100",
            "boatPropulsion": "foobar",
            "boatHullMaterial": "titanium",
            "boatIntendedUse": "boating",
            "boatIsInsured": True,
            "boatIsInspected": False,
        }
    )

    executed = superuser_api_client.execute(
        CREATE_BERTH_APPLICATION_MUTATION, input=create_berth_application_variables
    )
    assert executed == create_berth_application_result

    application = BerthApplication.objects.last()
    assert application.customer is application.boat.owner is None


def test_create_berth_application_by_customer(
    berth_customer_api_client,
    create_berth_application_variables,
    create_berth_application_result,
):
    boat_type = BoatTypeFactory()
    create_berth_application_variables["berthApplication"].update(
        {
            "boatType": boat_type.id,
            "boatLength": "2.00",
            "boatWidth": "3.00",
        }
    )

    executed = berth_customer_api_client.execute(
        CREATE_BERTH_APPLICATION_MUTATION, input=create_berth_application_variables
    )
    assert executed == create_berth_application_result

    application = BerthApplication.objects.last()
    assert application.boat.owner == application.customer
    assert berth_customer_api_client.user.customer == application.customer


def test_create_berth_application_wo_reason(
    superuser_api_client,
    create_berth_application_variables,
    create_berth_application_result,
):
    boat_type = BoatTypeFactory()
    create_berth_application_variables["berthApplication"].update(
        {
            "boatType": boat_type.id,
            "boatLength": "2.00",
            "boatWidth": "3.00",
        }
    )

    executed = superuser_api_client.execute(
        CREATE_BERTH_APPLICATION_MUTATION, input=create_berth_application_variables
    )

    assert executed == create_berth_application_result


def test_create_berth_application_with_existing_boat(
    superuser_api_client,
    create_berth_application_variables,
    create_berth_application_result,
):
    boat = BoatFactory(
        length="2.00",
        width="3.00",
        owner=None,
    )
    boat_id = to_global_id(BoatNode, boat.id)
    create_berth_application_variables["berthApplication"].update({"boatId": boat_id})

    executed = superuser_api_client.execute(
        CREATE_BERTH_APPLICATION_MUTATION, input=create_berth_application_variables
    )
    assert executed == create_berth_application_result

    application = BerthApplication.objects.last()
    assert application.customer is None
    assert application.boat.owner is None


def test_create_berth_application_with_existing_boat_by_customer(
    berth_customer_api_client,
    create_berth_application_variables,
    create_berth_application_result,
):
    user = berth_customer_api_client.user
    boat = BoatFactory(
        length="2.00",
        width="3.00",
        owner__user=user,
    )
    boat_id = to_global_id(BoatNode, boat.id)
    create_berth_application_variables["berthApplication"]["boatId"] = boat_id

    executed = berth_customer_api_client.execute(
        CREATE_BERTH_APPLICATION_MUTATION, input=create_berth_application_variables
    )
    assert executed == create_berth_application_result

    application = BerthApplication.objects.last()
    assert application.customer == user.customer
    assert application.boat.owner == user.customer


def test_create_berth_application_cannot_use_other_customer_boat(
    berth_customer_api_client, create_berth_application_variables
):
    boat = BoatFactory(length="2.00", width="3.00", owner=CustomerProfileFactory())
    boat_id = to_global_id(BoatNode, boat.id)
    create_berth_application_variables["berthApplication"]["boatId"] = boat_id

    executed = berth_customer_api_client.execute(
        CREATE_BERTH_APPLICATION_MUTATION, input=create_berth_application_variables
    )

    assert_doesnt_exist("Boat", executed)


@pytest.mark.parametrize("missing_field", ["boatType", "boatWidth", "boatLength"])
def test_create_berth_application_boat_id_or_type_and_length_and_width_required(
    superuser_api_client, create_berth_application_variables, missing_field
):
    boat_type = BoatTypeFactory()
    create_berth_application_variables["berthApplication"].update(
        {
            "boatType": boat_type.id,
            "boatLength": "2.00",
            "boatWidth": "3.00",
        }
    )

    create_berth_application_variables["berthApplication"].pop(missing_field)

    executed = superuser_api_client.execute(
        CREATE_BERTH_APPLICATION_MUTATION, input=create_berth_application_variables
    )

    assert_in_errors(
        'Either "boatId" or "boatType", "boatLength" and "boatWidth" are required',
        executed,
    )


def test_create_berth_application_cannot_use_boat_id_and_other_boat_fields(
    superuser_api_client, create_berth_application_variables
):

    boat = BoatFactory(length="2.00", width="3.00")
    boat_id = to_global_id(BoatNode, boat.id)

    create_berth_application_variables["berthApplication"].update(
        {"boatId": boat_id, "boatLength": boat.length}
    )

    executed = superuser_api_client.execute(
        CREATE_BERTH_APPLICATION_MUTATION, input=create_berth_application_variables
    )

    assert_in_errors(
        "Cannot use both boat ID and other boat field(s) at the same time",
        executed,
    )


UPDATE_BERTH_APPLICATION_MUTATION = """
mutation UpdateApplication($input: UpdateBerthApplicationInput!) {
    updateBerthApplication(input: $input) {
        berthApplication {
            id
            customer {
                id
                comment
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_services"],
    indirect=True,
)
def test_update_berth_application(api_client, berth_application, customer_profile):
    berth_application_id = to_global_id(BerthApplicationNode, berth_application.id)
    customer_id = to_global_id(ProfileNode, customer_profile.id)

    variables = {
        "id": berth_application_id,
        "customerId": customer_id,
    }

    assert berth_application.customer is None

    executed = api_client.execute(UPDATE_BERTH_APPLICATION_MUTATION, input=variables)

    assert executed == {
        "data": {
            "updateBerthApplication": {
                "berthApplication": {
                    "id": berth_application_id,
                    "customer": {
                        "id": customer_id,
                        "comment": customer_profile.comment,
                    },
                }
            }
        }
    }


UPDATE_BERTH_APPLICATION_BOAT_MUTATION = """
mutation UpdateApplicationBoat($input: UpdateBerthApplicationInput!) {
    updateBerthApplication(input: $input) {
        berthApplication {
            id
            boatType
            boatLength
            boatWidth
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_services"],
    indirect=True,
)
def test_update_berth_application_set_boat_fields(
    api_client, berth_application_with_customer
):
    berth_application_id = to_global_id(
        BerthApplicationNode, berth_application_with_customer.id
    )
    boat_type = BoatTypeFactory()

    variables = {
        "id": berth_application_id,
        "boatType": boat_type.id,
        "boatLength": "8.00",
        "boatWidth": "9.00",
    }

    executed = api_client.execute(
        UPDATE_BERTH_APPLICATION_BOAT_MUTATION, input=variables
    )

    assert executed == {
        "data": {
            "updateBerthApplication": {
                "berthApplication": {
                    "id": berth_application_id,
                    "boatType": str(boat_type.id),
                    "boatLength": "8.00",
                    "boatWidth": "9.00",
                }
            }
        }
    }


@pytest.mark.parametrize(
    "api_client",
    ["berth_services"],
    indirect=True,
)
def test_update_berth_application_set_boat_id(
    api_client, berth_application_with_customer
):
    berth_application_id = to_global_id(
        BerthApplicationNode, berth_application_with_customer.id
    )
    boat_type = BoatTypeFactory()
    boat = BoatFactory(
        boat_type=boat_type,
        length="8.00",
        width="9.00",
        owner=berth_application_with_customer.customer,
    )
    boat_id = to_global_id(BoatNode, boat.id)

    variables = {
        "id": berth_application_id,
        "boatId": boat_id,
    }

    executed = api_client.execute(
        UPDATE_BERTH_APPLICATION_BOAT_MUTATION, input=variables
    )

    assert executed == {
        "data": {
            "updateBerthApplication": {
                "berthApplication": {
                    "id": berth_application_id,
                    "boatType": str(boat_type.id),
                    "boatLength": "8.00",
                    "boatWidth": "9.00",
                }
            }
        }
    }


@pytest.mark.parametrize(
    "api_client",
    ["berth_services"],
    indirect=True,
)
def test_update_berth_application_no_application_id(api_client, customer_profile):
    variables = {
        "customerId": to_global_id(ProfileNode, customer_profile.id),
    }

    executed = api_client.execute(UPDATE_BERTH_APPLICATION_MUTATION, input=variables)

    assert_field_missing("id", executed)


@pytest.mark.parametrize(
    "api_client",
    ["berth_services"],
    indirect=True,
)
@pytest.mark.parametrize("status", ApplicationStatus.values)
def test_update_berth_application_no_customer_id(
    api_client, berth_application_with_customer, status
):
    berth_application_with_customer.lease = BerthLeaseFactory()
    berth_application_with_customer.status = status
    berth_application_with_customer.save()
    application_id = to_global_id(
        BerthApplicationNode, berth_application_with_customer.id
    )
    variables = {
        "id": application_id,
        "customerId": None,
    }

    executed = api_client.execute(UPDATE_BERTH_APPLICATION_MUTATION, input=variables)

    if status == ApplicationStatus.PENDING:
        assert executed == {
            "data": {
                "updateBerthApplication": {
                    "berthApplication": {"id": application_id, "customer": None}
                }
            }
        }
    else:
        assert_in_errors(
            "Customer cannot be disconnected from processed applications", executed
        )


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "berth_handler", "berth_supervisor", "harbor_services", "user"],
    indirect=True,
)
def test_update_berth_application_not_enough_permissions(
    api_client, berth_application, customer_profile
):
    berth_application_id = to_global_id(BerthApplicationNode, berth_application.id)
    customer_id = to_global_id(ProfileNode, customer_profile.id)

    variables = {
        "id": berth_application_id,
        "customerId": customer_id,
    }

    executed = api_client.execute(UPDATE_BERTH_APPLICATION_MUTATION, input=variables)

    assert berth_application.customer is None
    assert_not_enough_permissions(executed)


DELETE_BERTH_APPLICATION_MUTATION = """
mutation DeleteBerthApplication($input: DeleteBerthApplicationMutationInput!) {
    deleteBerthApplication(input: $input) {
        __typename
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_services"],
    indirect=True,
)
def test_delete_berth_application(api_client, berth_application, customer_profile):
    variables = {
        "id": to_global_id(BerthApplicationNode, berth_application.id),
    }

    assert BerthApplication.objects.count() == 1

    api_client.execute(DELETE_BERTH_APPLICATION_MUTATION, input=variables)

    assert BerthApplication.objects.count() == 0


def test_delete_berth_application_by_customer(
    berth_customer_api_client, customer_profile
):
    berth_application = BerthApplicationFactory(
        status=ApplicationStatus.PENDING, customer=customer_profile
    )
    variables = {
        "id": to_global_id(BerthApplicationNode, berth_application.id),
    }
    customer_profile.user = berth_customer_api_client.user
    customer_profile.save()
    assert BerthApplication.objects.count() == 1

    berth_customer_api_client.execute(
        DELETE_BERTH_APPLICATION_MUTATION, input=variables
    )

    assert BerthApplication.objects.count() == 0


def test_delete_berth_application_by_wrong_customer(
    berth_customer_api_client, customer_profile, berth_customer_user
):
    berth_application = BerthApplicationFactory(
        status=ApplicationStatus.PENDING, customer=customer_profile
    )
    variables = {
        "id": to_global_id(BerthApplicationNode, berth_application.id),
    }
    assert berth_customer_api_client.user != berth_customer_user
    customer_profile.user = berth_customer_user  # different customer
    customer_profile.save()
    assert BerthApplication.objects.count() == 1

    berth_customer_api_client.execute(
        DELETE_BERTH_APPLICATION_MUTATION, input=variables
    )

    assert BerthApplication.objects.count() == 1


@pytest.mark.parametrize(
    "application_status",
    [
        ApplicationStatus.OFFER_GENERATED,
        ApplicationStatus.OFFER_SENT,
        ApplicationStatus.REJECTED,
        ApplicationStatus.NO_SUITABLE_BERTHS,
        ApplicationStatus.HANDLED,
        ApplicationStatus.EXPIRED,
    ],
)
def test_delete_berth_application_by_customer_invalid_status(
    berth_customer_api_client, customer_profile, application_status
):
    berth_application = BerthApplicationFactory(
        status=ApplicationStatus.PENDING, customer=customer_profile
    )
    variables = {
        "id": to_global_id(BerthApplicationNode, berth_application.id),
    }
    customer_profile.user = berth_customer_api_client.user
    customer_profile.save()
    assert BerthApplication.objects.count() == 1

    berth_customer_api_client.execute(
        DELETE_BERTH_APPLICATION_MUTATION, input=variables
    )

    assert BerthApplication.objects.count() == 0


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_delete_berth_not_enough_permissions(api_client, berth_application):
    variables = {
        "id": to_global_id(BerthApplicationNode, berth_application.id),
    }

    assert BerthApplication.objects.count() == 1

    executed = api_client.execute(DELETE_BERTH_APPLICATION_MUTATION, input=variables)

    assert BerthApplication.objects.count() == 1
    assert_not_enough_permissions(executed)


REJECT_BERTH_APPLICATION_MUTATION = """
mutation RejectBerthApplicationMutation($input: RejectBerthApplicationMutationInput!) {
    rejectBerthApplication(input: $input) {
        __typename
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_services"],
    indirect=True,
)
def test_reject_berth_application(
    api_client,
    berth_application,
    customer_profile,
    notification_template_berth_application_rejected,
):
    variables = {
        "id": to_global_id(BerthApplicationNode, berth_application.id),
    }

    assert (
        BerthApplication.objects.filter(
            status=ApplicationStatus.NO_SUITABLE_BERTHS
        ).count()
        == 0
    )

    api_client.execute(REJECT_BERTH_APPLICATION_MUTATION, input=variables)

    assert (
        BerthApplication.objects.filter(
            status=ApplicationStatus.NO_SUITABLE_BERTHS
        ).count()
        == 1
    )
    assert len(mail.outbox) == 1
    assert (
        mail.outbox[0].subject
        == f"test berth application rejected subject, event: {berth_application.first_name}!"
    )
    assert mail.outbox[0].body == "test berth application rejected body text!"
    assert mail.outbox[0].to == [berth_application.email]

    assert mail.outbox[0].alternatives == [
        (
            "<b>test berth application rejected body HTML!</b>",
            "text/html",
        )
    ]


@pytest.mark.parametrize(
    "api_client",
    ["berth_services"],
    indirect=True,
)
def test_reject_berth_application_fails_for_lease(
    api_client, berth_application, customer_profile
):
    variables = {
        "id": to_global_id(BerthApplicationNode, berth_application.id),
    }
    BerthLeaseFactory(application=berth_application)

    executed = api_client.execute(REJECT_BERTH_APPLICATION_MUTATION, input=variables)

    assert_in_errors("Application has a lease", executed)

    assert (
        BerthApplication.objects.filter(
            status=ApplicationStatus.NO_SUITABLE_BERTHS
        ).count()
        == 0
    )


def test_delete_berth_application_inexistent_application(superuser_api_client):
    variables = {
        "id": to_global_id(BerthApplicationNode, random.randint(0, 100)),
    }

    executed = superuser_api_client.execute(
        DELETE_BERTH_APPLICATION_MUTATION, input=variables
    )

    assert_doesnt_exist("BerthApplication", executed)


EXTEND_BERTH_APPLICATION_MUTATION = """
mutation ExtendBerthApplicationMutation($input: ExtendBerthApplicationMutationInput!) {
    extendBerthApplication(input: $input) {
        __typename
    }
}
"""


def test_extend_berth_application(customer_profile):
    berth_application = BerthApplicationFactory(
        status=ApplicationStatus.NO_SUITABLE_BERTHS, customer=customer_profile
    )

    variables = {
        "id": to_global_id(BerthApplicationNode, berth_application.id),
    }

    api_client = create_api_client(user=customer_profile.user)
    api_client.execute(EXTEND_BERTH_APPLICATION_MUTATION, input=variables)

    berth_application = BerthApplication.objects.get(id=berth_application.id)
    assert berth_application.status == ApplicationStatus.PENDING
    assert berth_application.priority == ApplicationPriority.LOW


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_extend_berth_application_not_enough_permissions(api_client, berth_application):
    berth_application.status = ApplicationStatus.NO_SUITABLE_BERTHS
    berth_application.save()

    variables = {
        "id": to_global_id(BerthApplicationNode, berth_application.id),
    }

    executed = api_client.execute(EXTEND_BERTH_APPLICATION_MUTATION, input=variables)

    assert_not_enough_permissions(executed)


@pytest.mark.parametrize(
    "status",
    [
        # BerthApplication with no lease can only be
        # PENDING, EXPIRED, NO_SUITABLE_BERTH
        ApplicationStatus.PENDING,
        ApplicationStatus.EXPIRED,
    ],
)
def test_extend_berth_application_not_rejected(
    superuser_api_client, berth_application, status
):
    berth_application.status = status
    berth_application.save()

    variables = {
        "id": to_global_id(BerthApplicationNode, berth_application.id),
    }

    executed = superuser_api_client.execute(
        EXTEND_BERTH_APPLICATION_MUTATION, input=variables
    )

    assert_in_errors("Cannot extend applications that have not been rejected", executed)


CREATE_WINTER_STORAGE_APPLICATION_MUTATION = """
mutation createWinterStorageApplication($input: CreateWinterStorageApplicationMutationInput!) {
    createWinterStorageApplication(input: $input) {
        winterStorageApplication {
            areaType
            winterStorageAreaChoices {
                winterStorageArea {
                    id
                }
            }
            boatWidth
            boatLength
        }
    }
}
"""


def test_create_winter_storage_application(superuser_api_client):
    winter_area = WinterStorageAreaFactory()
    boat_type = BoatTypeFactory()

    winter_area_node_id = to_global_id(WinterStorageAreaNode, winter_area.id)

    variables = {
        "winterStorageApplication": {
            "language": "en",
            "firstName": "John",
            "lastName": "Doe",
            "phoneNumber": "1234567890",
            "email": "john.doe@example.com",
            "address": "Mannerheimintie 1",
            "zipCode": "00100",
            "municipality": "Helsinki",
            "boatType": boat_type.id,
            "boatWidth": "2.00",
            "boatLength": "3.00",
            "informationAccuracyConfirmed": True,
            "acceptFitnessNews": False,
            "acceptLibraryNews": False,
            "acceptOtherCultureNews": False,
            "acceptBoatingNewsletter": True,
            "storageMethod": "ON_TRESTLES",
            "chosenAreas": [{"winterAreaId": winter_area_node_id, "priority": 1}],
        }
    }

    executed = superuser_api_client.execute(
        CREATE_WINTER_STORAGE_APPLICATION_MUTATION, input=variables
    )

    assert executed == {
        "data": {
            "createWinterStorageApplication": {
                "winterStorageApplication": {
                    "areaType": "MARKED",
                    "winterStorageAreaChoices": [
                        {"winterStorageArea": {"id": winter_area_node_id}}
                    ],
                    "boatWidth": "2.00",
                    "boatLength": "3.00",
                }
            }
        }
    }


def test_create_winter_storage_application_decimal_field_floats(superuser_api_client):
    """Related to an issue where the float would end up into a notification
    template looking like 2.02 -> 2.020000000000000017763568394002504646778106689453125.

    Ticket: PT-1436
    """
    winter_area = WinterStorageAreaFactory()
    boat_type = BoatTypeFactory()

    winter_area_node_id = to_global_id(WinterStorageAreaNode, winter_area.id)

    variables = {
        "winterStorageApplication": {
            "language": "en",
            "firstName": "John",
            "lastName": "Doe",
            "phoneNumber": "1234567890",
            "email": "john.doe@example.com",
            "address": "Mannerheimintie 1",
            "zipCode": "00100",
            "municipality": "Helsinki",
            "boatType": boat_type.id,
            "boatWidth": 2.02,
            "boatLength": 3.1,
            "informationAccuracyConfirmed": True,
            "acceptFitnessNews": False,
            "acceptLibraryNews": False,
            "acceptOtherCultureNews": False,
            "acceptBoatingNewsletter": True,
            "storageMethod": "ON_TRESTLES",
            "chosenAreas": [{"winterAreaId": winter_area_node_id, "priority": 1}],
        }
    }

    executed = superuser_api_client.execute(
        CREATE_WINTER_STORAGE_APPLICATION_MUTATION, input=variables
    )

    assert executed == {
        "data": {
            "createWinterStorageApplication": {
                "winterStorageApplication": {
                    "areaType": "MARKED",
                    "winterStorageAreaChoices": [
                        {"winterStorageArea": {"id": winter_area_node_id}}
                    ],
                    # Floats are handled correctly
                    "boatWidth": "2.02",
                    "boatLength": "3.1",
                }
            }
        }
    }


def test_create_winter_storage_application_with_existing_boat(superuser_api_client):
    winter_area = WinterStorageAreaFactory()
    boat = BoatFactory(width="5.00", length="6.00")
    boat_id = to_global_id(BoatNode, boat.id)
    winter_area_node_id = to_global_id(WinterStorageAreaNode, winter_area.id)

    variables = {
        "winterStorageApplication": {
            "language": "en",
            "firstName": "John",
            "lastName": "Doe",
            "phoneNumber": "1234567890",
            "email": "john.doe@example.com",
            "address": "Mannerheimintie 1",
            "zipCode": "00100",
            "municipality": "Helsinki",
            "boatId": boat_id,
            "informationAccuracyConfirmed": True,
            "acceptFitnessNews": False,
            "acceptLibraryNews": False,
            "acceptOtherCultureNews": False,
            "acceptBoatingNewsletter": True,
            "storageMethod": "ON_TRESTLES",
            "chosenAreas": [{"winterAreaId": winter_area_node_id, "priority": 1}],
        }
    }

    executed = superuser_api_client.execute(
        CREATE_WINTER_STORAGE_APPLICATION_MUTATION, input=variables
    )

    assert executed == {
        "data": {
            "createWinterStorageApplication": {
                "winterStorageApplication": {
                    "areaType": "MARKED",
                    "winterStorageAreaChoices": [
                        {"winterStorageArea": {"id": winter_area_node_id}}
                    ],
                    "boatWidth": "5.00",
                    "boatLength": "6.00",
                }
            }
        }
    }


UPDATE_WINTER_STORAGE_APPLICATION_MUTATION = """
mutation UpdateApplication($input: UpdateWinterStorageApplicationInput!) {
    updateWinterStorageApplication(input: $input) {
        winterStorageApplication {
            id
            customer {
                id
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_services"],
    indirect=True,
)
def test_update_winter_storage_application(
    api_client, winter_storage_application, customer_profile
):
    application_id = to_global_id(
        WinterStorageApplicationNode, winter_storage_application.id
    )
    customer_id = to_global_id(ProfileNode, customer_profile.id)

    variables = {
        "id": application_id,
        "customerId": customer_id,
    }

    assert winter_storage_application.customer is None

    executed = api_client.execute(
        UPDATE_WINTER_STORAGE_APPLICATION_MUTATION, input=variables
    )

    assert executed == {
        "data": {
            "updateWinterStorageApplication": {
                "winterStorageApplication": {
                    "id": application_id,
                    "customer": {"id": customer_id},
                }
            }
        }
    }


@pytest.mark.parametrize(
    "api_client",
    ["berth_services"],
    indirect=True,
)
def test_update_winter_storage_application_no_application_id(
    api_client, customer_profile
):
    variables = {
        "customerId": to_global_id(ProfileNode, customer_profile.id),
    }

    executed = api_client.execute(
        UPDATE_WINTER_STORAGE_APPLICATION_MUTATION, input=variables
    )

    assert_field_missing("id", executed)


@pytest.mark.parametrize(
    "api_client",
    ["berth_services"],
    indirect=True,
)
@pytest.mark.parametrize("status", ApplicationStatus.values)
def test_update_winter_storage_application_no_customer_id(
    api_client, winter_storage_application_with_customer, status
):
    winter_storage_application_with_customer.status = status
    winter_storage_application_with_customer.save()
    application_id = to_global_id(
        WinterStorageApplicationNode, winter_storage_application_with_customer.id
    )
    variables = {
        "id": application_id,
        "customerId": None,
    }

    executed = api_client.execute(
        UPDATE_WINTER_STORAGE_APPLICATION_MUTATION, input=variables
    )

    if status == ApplicationStatus.PENDING:
        assert executed == {
            "data": {
                "updateWinterStorageApplication": {
                    "winterStorageApplication": {
                        "id": application_id,
                        "customer": None,
                    }
                }
            }
        }
    else:
        assert_in_errors(
            "Customer cannot be disconnected from processed applications", executed
        )


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "berth_handler", "berth_supervisor", "harbor_services", "user"],
    indirect=True,
)
def test_update_winter_storage_application_not_enough_permissions(
    api_client, winter_storage_application, customer_profile
):
    winter_storage_application_id = to_global_id(
        WinterStorageApplicationNode, winter_storage_application.id
    )
    customer_id = to_global_id(ProfileNode, customer_profile.id)

    variables = {
        "id": winter_storage_application_id,
        "customerId": customer_id,
    }

    executed = api_client.execute(
        UPDATE_WINTER_STORAGE_APPLICATION_MUTATION, input=variables
    )

    assert winter_storage_application.customer is None
    assert_not_enough_permissions(executed)


DELETE_WINTER_STORAGE_APPLICATION_MUTATION = """
mutation DeleteWinterStorageApplication($input: DeleteWinterStorageApplicationMutationInput!) {
    deleteWinterStorageApplication(input: $input) {
        __typename
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_services"],
    indirect=True,
)
def test_delete_winter_storage_application(
    api_client, winter_storage_application, customer_profile
):
    variables = {
        "id": to_global_id(WinterStorageApplicationNode, winter_storage_application.id),
    }

    assert WinterStorageApplication.objects.count() == 1

    api_client.execute(DELETE_WINTER_STORAGE_APPLICATION_MUTATION, input=variables)

    assert WinterStorageApplication.objects.count() == 0


@pytest.mark.parametrize(
    "api_client",
    ["api_client", "user", "berth_supervisor", "berth_handler"],
    indirect=True,
)
def test_delete_winter_storage_application_not_enough_permissions(
    api_client, winter_storage_application
):
    variables = {
        "id": to_global_id(WinterStorageApplicationNode, winter_storage_application.id),
    }

    assert WinterStorageApplication.objects.count() == 1

    executed = api_client.execute(
        DELETE_WINTER_STORAGE_APPLICATION_MUTATION, input=variables
    )

    assert WinterStorageApplication.objects.count() == 1
    assert_not_enough_permissions(executed)


def test_delete_winter_storage_application_inexistent_application(
    superuser_api_client,
):
    variables = {
        "id": to_global_id(WinterStorageApplicationNode, random.randint(0, 100)),
    }

    executed = superuser_api_client.execute(
        DELETE_WINTER_STORAGE_APPLICATION_MUTATION, input=variables
    )

    assert_doesnt_exist("WinterStorageApplication", executed)


UPDATE_BERTH_APPLICATION_OWNER_MUTATION = """
mutation UpdateApplication($input: UpdateBerthApplicationInput!) {
    updateBerthApplication(input: $input) {
        berthApplication {
            id
            language
            firstName
            lastName
            phoneNumber
            email
            address
            zipCode
            municipality
            boatWidth
            boatLength
            acceptFitnessNews
            acceptLibraryNews
            acceptOtherCultureNews
            acceptBoatingNewsletter
            harborChoices {
                harbor {
                    id
                }
            }
        }
    }
}
"""


def test_update_berth_application_by_owner(berth_customer_api_client, customer_profile):
    berth_application = BerthApplicationFactory(customer=customer_profile)
    berth_application_id = to_global_id(BerthApplicationNode, berth_application.id)
    remove_choice = HarborChoiceFactory(application=berth_application)

    berth = BerthFactory()
    harbor_node_id = to_global_id(HarborNode, berth.pier.harbor.id)

    customer_profile.user = berth_customer_api_client.user
    customer_profile.save()

    berth_application.boat.width = "4.00"
    berth_application.boat.length = "5.00"
    berth_application.boat.save()

    variables = {
        "id": berth_application_id,
        "language": "en",
        "firstName": "John",
        "lastName": "Doe",
        "phoneNumber": "1234567890",
        "email": "john.doe@example.com",
        "address": "Mannerheimintie 1",
        "zipCode": "00100",
        "municipality": "Helsinki",
        "boatWidth": "2.00",
        "boatLength": "3.00",
        "acceptFitnessNews": False,
        "acceptLibraryNews": False,
        "acceptOtherCultureNews": False,
        "acceptBoatingNewsletter": True,
        "addChoices": [{"harborId": harbor_node_id, "priority": 1}],
        "removeChoices": [remove_choice.priority],
    }

    assert berth_application.harborchoice_set.count() == 1
    assert berth_application.changes.count() == 0

    executed = berth_customer_api_client.execute(
        UPDATE_BERTH_APPLICATION_OWNER_MUTATION, input=variables
    )

    assert berth_application.harborchoice_set.count() == 1
    assert berth_application.changes.count() == 2

    application_change = berth_application.changes.filter(
        change_list__icontains="old"
    ).first()
    assert (
        application_change.change_list
        == f"Old harbor choices:\n{remove_choice.priority}: {remove_choice.harbor.name}\n\n"
        f"New harbor choices:\n1: {berth.pier.harbor.name}"
    )

    assert executed == {
        "data": {
            "updateBerthApplication": {
                "berthApplication": {
                    "id": berth_application_id,
                    "language": "EN",
                    "firstName": "John",
                    "lastName": "Doe",
                    "phoneNumber": "1234567890",
                    "email": "john.doe@example.com",
                    "address": "Mannerheimintie 1",
                    "zipCode": "00100",
                    "municipality": "Helsinki",
                    "boatWidth": "2.00",
                    "boatLength": "3.00",
                    "acceptFitnessNews": False,
                    "acceptLibraryNews": False,
                    "acceptOtherCultureNews": False,
                    "acceptBoatingNewsletter": True,
                    "harborChoices": [{"harbor": {"id": harbor_node_id}}],
                }
            }
        }
    }


def test_update_berth_application_by_owner_cant_update_customer(
    berth_customer_api_client, customer_profile
):
    berth_application = BerthApplicationFactory(customer=customer_profile)
    berth_application_id = to_global_id(BerthApplicationNode, berth_application.id)
    other_customer = CustomerProfileFactory()

    customer_profile.user = berth_customer_api_client.user
    customer_profile.save()

    variables = {
        "id": berth_application_id,
        "customerId": to_global_id(ProfileNode, other_customer.id),
    }

    executed = berth_customer_api_client.execute(
        UPDATE_BERTH_APPLICATION_OWNER_MUTATION, input=variables
    )

    assert_in_errors(
        "A customer cannot modify the customer connected to the application", executed
    )


@pytest.mark.parametrize(
    "status",
    [ApplicationStatus.NO_SUITABLE_BERTHS, ApplicationStatus.EXPIRED],
)
def test_update_berth_application_by_owner_invalid_status(
    berth_customer_api_client, customer_profile, status
):
    berth_application = BerthApplicationFactory(
        status=status, customer=customer_profile
    )
    berth_application_id = to_global_id(BerthApplicationNode, berth_application.id)
    other_customer = CustomerProfileFactory()

    customer_profile.user = berth_customer_api_client.user
    customer_profile.save()

    variables = {
        "id": berth_application_id,
        "customerId": to_global_id(ProfileNode, other_customer.id),
    }

    executed = berth_customer_api_client.execute(
        UPDATE_BERTH_APPLICATION_OWNER_MUTATION, input=variables
    )

    assert_in_errors(
        "Cannot modify the application once it has been processed", executed
    )


UPDATE_WINTER_STORAGE_APPLICATION_OWNER_MUTATION = """
mutation UpdateApplication($input: UpdateWinterStorageApplicationInput!) {
    updateWinterStorageApplication(input: $input) {
        winterStorageApplication {
            id
            language
            firstName
            lastName
            phoneNumber
            email
            address
            zipCode
            municipality
            boatWidth
            boatLength
            acceptFitnessNews
            acceptLibraryNews
            acceptOtherCultureNews
            acceptBoatingNewsletter
            winterStorageAreaChoices {
                winterStorageArea {
                    id
                }
            }
        }
    }
}
"""


def test_update_winter_storage_application_by_owner(
    berth_customer_api_client, customer_profile
):
    winter_storage_application = WinterStorageApplicationFactory(
        customer=customer_profile
    )
    winter_storage_application_id = to_global_id(
        WinterStorageApplicationNode, winter_storage_application.id
    )
    remove_choice = WinterAreaChoiceFactory(application=winter_storage_application)

    place = WinterStoragePlaceFactory()
    area_node_id = to_global_id(
        WinterStorageAreaNode, place.winter_storage_section.area.id
    )

    customer_profile.user = berth_customer_api_client.user
    customer_profile.save()

    winter_storage_application.boat.width = "4.00"
    winter_storage_application.boat.length = "5.00"
    winter_storage_application.boat.save()

    variables = {
        "id": winter_storage_application_id,
        "language": "en",
        "firstName": "John",
        "lastName": "Doe",
        "phoneNumber": "1234567890",
        "email": "john.doe@example.com",
        "address": "Mannerheimintie 1",
        "zipCode": "00100",
        "municipality": "Helsinki",
        "boatWidth": "2.00",
        "boatLength": "3.00",
        "acceptFitnessNews": False,
        "acceptLibraryNews": False,
        "acceptOtherCultureNews": False,
        "acceptBoatingNewsletter": True,
        "addChoices": [{"winterAreaId": area_node_id, "priority": 1}],
        "removeChoices": [remove_choice.priority],
    }

    assert winter_storage_application.winterstorageareachoice_set.count() == 1
    assert winter_storage_application.changes.count() == 0

    executed = berth_customer_api_client.execute(
        UPDATE_WINTER_STORAGE_APPLICATION_OWNER_MUTATION, input=variables
    )

    assert winter_storage_application.winterstorageareachoice_set.count() == 1
    assert winter_storage_application.changes.count() == 2

    application_change = winter_storage_application.changes.filter(
        change_list__icontains="old"
    ).first()
    assert (
        application_change.change_list
        == f"Old area choices:\n{remove_choice.priority}: {remove_choice.winter_storage_area.name}\n\n"
        f"New area choices:\n1: {place.winter_storage_section.area.name}"
    )

    assert executed == {
        "data": {
            "updateWinterStorageApplication": {
                "winterStorageApplication": {
                    "id": winter_storage_application_id,
                    "language": "EN",
                    "firstName": "John",
                    "lastName": "Doe",
                    "phoneNumber": "1234567890",
                    "email": "john.doe@example.com",
                    "address": "Mannerheimintie 1",
                    "zipCode": "00100",
                    "municipality": "Helsinki",
                    "boatWidth": "2.00",
                    "boatLength": "3.00",
                    "acceptFitnessNews": False,
                    "acceptLibraryNews": False,
                    "acceptOtherCultureNews": False,
                    "acceptBoatingNewsletter": True,
                    "winterStorageAreaChoices": [
                        {"winterStorageArea": {"id": area_node_id}}
                    ],
                }
            }
        }
    }


def test_update_winter_storage_application_by_owner_cant_update_customer(
    berth_customer_api_client, customer_profile
):
    winter_storage_application = WinterStorageApplicationFactory(
        customer=customer_profile
    )
    winter_storage_application_id = to_global_id(
        WinterStorageApplicationNode, winter_storage_application.id
    )
    other_customer = CustomerProfileFactory()

    customer_profile.user = berth_customer_api_client.user
    customer_profile.save()

    variables = {
        "id": winter_storage_application_id,
        "customerId": to_global_id(ProfileNode, other_customer.id),
    }

    executed = berth_customer_api_client.execute(
        UPDATE_WINTER_STORAGE_APPLICATION_OWNER_MUTATION, input=variables
    )

    assert_in_errors(
        "A customer cannot modify the customer connected to the application", executed
    )


@pytest.mark.parametrize(
    "status",
    [ApplicationStatus.NO_SUITABLE_BERTHS, ApplicationStatus.EXPIRED],
)
def test_update_winter_storage_application_by_owner_invalid_status(
    berth_customer_api_client, customer_profile, status
):
    winter_storage_application = WinterStorageApplicationFactory(
        status=status, customer=customer_profile
    )
    winter_storage_application_id = to_global_id(
        WinterStorageApplicationNode, winter_storage_application.id
    )

    customer_profile.user = berth_customer_api_client.user
    customer_profile.save()
    # winter_storage_application.customer = customer_profile
    # winter_storage_application.save()

    variables = {"id": winter_storage_application_id, "firstName": "Invalid comment"}

    executed = berth_customer_api_client.execute(
        UPDATE_WINTER_STORAGE_APPLICATION_OWNER_MUTATION, input=variables
    )

    assert_in_errors(
        "Cannot modify the application once it has been processed", executed
    )
