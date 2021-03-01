import random

import pytest
from django.core import mail

from berth_reservations.tests.utils import (
    assert_doesnt_exist,
    assert_field_missing,
    assert_in_errors,
    assert_not_enough_permissions,
)
from customers.schema import ProfileNode
from leases.tests.factories import BerthLeaseFactory
from utils.relay import to_global_id

from ..enums import ApplicationStatus
from ..models import BerthApplication, WinterStorageApplication
from ..new_schema import BerthApplicationNode
from ..new_schema.types import WinterStorageApplicationNode

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
    "api_client", ["berth_services"], indirect=True,
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


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
)
def test_update_berth_application_no_application_id(api_client, customer_profile):
    variables = {
        "customerId": to_global_id(ProfileNode, customer_profile.id),
    }

    executed = api_client.execute(UPDATE_BERTH_APPLICATION_MUTATION, input=variables)

    assert_field_missing("id", executed)


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
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
    "api_client", ["berth_services"], indirect=True,
)
def test_delete_berth_application(api_client, berth_application, customer_profile):
    variables = {
        "id": to_global_id(BerthApplicationNode, berth_application.id),
    }

    assert BerthApplication.objects.count() == 1

    api_client.execute(DELETE_BERTH_APPLICATION_MUTATION, input=variables)

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
    "api_client", ["berth_services"], indirect=True,
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
        ("<b>test berth application rejected body HTML!</b>", "text/html",)
    ]


@pytest.mark.parametrize(
    "api_client", ["berth_services"], indirect=True,
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
    "api_client", ["berth_services"], indirect=True,
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
    "api_client", ["berth_services"], indirect=True,
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
    "api_client", ["berth_services"], indirect=True,
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
    "api_client", ["berth_services"], indirect=True,
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
