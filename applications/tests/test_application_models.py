import pytest
from django.core.exceptions import ValidationError

from ..enums import ApplicationStatus


def test_berth_application_without_lease_valid_statuses(berth_application):
    new_status = ApplicationStatus.PENDING
    berth_application.lease = None
    berth_application.status = new_status

    berth_application.save()

    assert berth_application.status == new_status


def test_berth_application_without_lease_invalid_statuses(berth_application):
    new_status = ApplicationStatus.OFFER_GENERATED
    berth_application.lease = None
    berth_application.status = new_status

    with pytest.raises(ValidationError) as exception:
        berth_application.save()

    error_msg = str(exception.value)
    assert new_status.name in error_msg
    assert "BerthApplication with no lease can only be" in error_msg
