import pytest
from dateutil.utils import today

from applications.enums import ApplicationAreaType
from berth_reservations.tests.utils import assert_in_errors
from utils.relay import to_global_id

from ..enums import LeaseStatus
from ..schema import WinterStorageLeaseNode

CONFIRM_PAYMENT_MUTATION = """
mutation NEW_STICKER_NUMBER($input: AssignNewStickerNumberMutationInput!) {
    assignNewStickerNumber(input: $input) {
        stickerNumber
    }
}
"""


@pytest.mark.skip(
    reason="temporarily disabled so that retry logic can be tested in test env"
)
def test_assign_new_sticker_number_error_when_unpaid(
    sticker_sequences, superuser_api_client, winter_storage_lease
):
    variables = {
        "leaseId": to_global_id(WinterStorageLeaseNode, winter_storage_lease.id)
    }

    executed = superuser_api_client.execute(CONFIRM_PAYMENT_MUTATION, input=variables)

    assert_in_errors("Lease must be in PAID status", executed)


@pytest.mark.skip(
    reason="temporarily disabled so that retry logic can be tested in test env"
)
def test_assign_new_sticker_number_error_when_marked_lease(
    sticker_sequences,
    superuser_api_client,
    winter_storage_lease,
    winter_storage_application,
):
    variables = {
        "leaseId": to_global_id(WinterStorageLeaseNode, winter_storage_lease.id)
    }
    winter_storage_application.area_type = ApplicationAreaType.MARKED
    winter_storage_application.save()

    winter_storage_lease.status = LeaseStatus.PAID
    winter_storage_lease.application = winter_storage_application
    winter_storage_lease.save()

    executed = superuser_api_client.execute(CONFIRM_PAYMENT_MUTATION, input=variables)

    assert_in_errors("Lease must refer to unmarked area", executed)


QUERY_WINTER_STORAGE_LEASE = """
query GetWinterStorageLease {
    winterStorageLease(id: "%s") {
        id
        stickerNumber
        stickerSeason
        stickerPosted
    }
}
"""


@pytest.mark.skip(
    reason="temporarily disabled so that retry logic can be tested in test env"
)
def test_assign_new_sticker_number(
    sticker_sequences,
    superuser_api_client,
    winter_storage_lease,
    winter_storage_application,
):
    lease_id = to_global_id(WinterStorageLeaseNode, winter_storage_lease.id)
    variables = {"leaseId": lease_id}
    winter_storage_application.area_type = ApplicationAreaType.UNMARKED
    winter_storage_application.save()

    winter_storage_lease.status = LeaseStatus.PAID
    winter_storage_lease.application = winter_storage_application
    winter_storage_lease.save()

    executed = superuser_api_client.execute(CONFIRM_PAYMENT_MUTATION, input=variables)

    assert executed["data"]["assignNewStickerNumber"]["stickerNumber"] == 1

    query = QUERY_WINTER_STORAGE_LEASE % lease_id
    executed = superuser_api_client.execute(query)

    assert executed["data"]["winterStorageLease"]["stickerNumber"] == 1

    sticker_season = executed["data"]["winterStorageLease"]["stickerSeason"]
    assert len(sticker_season) == 9


@pytest.mark.skip(
    reason="temporarily disabled so that retry logic can be tested in test env"
)
def test_assign_new_sticker_number_resets_posted_date(
    sticker_sequences,
    superuser_api_client,
    winter_storage_lease,
    winter_storage_application,
):
    lease_id = to_global_id(WinterStorageLeaseNode, winter_storage_lease.id)
    variables = {"leaseId": lease_id}
    winter_storage_application.area_type = ApplicationAreaType.UNMARKED
    winter_storage_application.save()

    date_to_test = today()

    winter_storage_lease.status = LeaseStatus.PAID
    winter_storage_lease.application = winter_storage_application
    winter_storage_lease.sticker_posted = date_to_test
    winter_storage_lease.save()

    executed = superuser_api_client.execute(QUERY_WINTER_STORAGE_LEASE % lease_id)
    assert executed["data"]["winterStorageLease"]["stickerPosted"] == str(
        date_to_test.date()
    )

    superuser_api_client.execute(CONFIRM_PAYMENT_MUTATION, input=variables)
    executed = superuser_api_client.execute(QUERY_WINTER_STORAGE_LEASE % lease_id)
    assert executed["data"]["winterStorageLease"]["stickerPosted"] is None


SET_STICKERS_POSTED_MUTATION = """
mutation NEW_STICKER_NUMBER($input: SetStickersPostedMutationInput!) {
    setStickersPosted(input: $input) {
        clientMutationId
    }
}
"""


@pytest.mark.skip(
    reason="temporarily disabled so that retry logic can be tested in test env"
)
def test_set_stickers_posted(superuser_api_client, winter_storage_lease):
    lease_id = to_global_id(WinterStorageLeaseNode, winter_storage_lease.id)

    winter_storage_lease.sticker_number = 1
    winter_storage_lease.save()

    variables = {"leaseIds": [lease_id], "date": today()}

    superuser_api_client.execute(SET_STICKERS_POSTED_MUTATION, input=variables)
    executed = superuser_api_client.execute(QUERY_WINTER_STORAGE_LEASE % lease_id)

    assert executed["data"]["winterStorageLease"]["stickerPosted"] == str(
        variables["date"].date()
    )


def test_set_stickers_posted_error_when_no_sticker_number(
    superuser_api_client, winter_storage_lease
):
    lease_id = to_global_id(WinterStorageLeaseNode, winter_storage_lease.id)
    variables = {"leaseIds": [lease_id], "date": today()}

    executed = superuser_api_client.execute(
        SET_STICKERS_POSTED_MUTATION, input=variables
    )

    assert_in_errors("All leases must have an assigned sticker number", executed)
