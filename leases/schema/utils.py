from datetime import date
from typing import Type, Union

from anymail.exceptions import AnymailError
from babel.dates import format_date
from dateutil.utils import today
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django_ilmoitin.utils import send_notification

from berth_reservations.exceptions import VenepaikkaGraphQLError
from customers.services import ProfileService
from utils.email import is_valid_email
from utils.relay import get_node_from_global_id, to_global_id

from ..enums import LeaseStatus
from ..models import BerthLease, WinterStorageLease
from ..notifications import NotificationType


def parse_invoicing_result(node_type):
    """Wrapper function to allow reusing the parse function with different Node types"""

    def parse_to_dict(object):
        """Util function to parse a dict of {"UUID": "message"} into {"id": "UUID", "error": "message"} """
        id, error = list(object.items())[0]
        return {"id": to_global_id(node_type, id), "error": error}

    return parse_to_dict


def terminate_lease(
    info,
    lease_id: str,
    lease_type: Union[Type],
    notification_type: NotificationType,
    end_date: date = None,
    profile_token: str = None,
) -> Union[BerthLease, WinterStorageLease]:

    lease: Union[BerthLease, WinterStorageLease] = get_node_from_global_id(
        info, lease_id, only_type=lease_type, nullable=False,
    )

    if lease.status != LeaseStatus.PAID:
        raise VenepaikkaGraphQLError(_(f"Lease is not paid: {lease.status}"))

    lease.status = LeaseStatus.TERMINATED
    lease.end_date = end_date or today().date()

    language = (
        lease.application.language if lease.application else settings.LANGUAGES[0][0]
    )

    if profile_token:
        profile_service = ProfileService(profile_token=profile_token)
        profile = profile_service.get_profile(lease.customer.id)
        email = profile.email
    elif lease.application:
        email = lease.application.email
    else:
        raise VenepaikkaGraphQLError(
            _("The lease has no email and no profile token was provided")
        )

    if not is_valid_email(email):
        raise VenepaikkaGraphQLError(_("Missing customer email"))

    try:
        lease.save()
        send_notification(
            email,
            notification_type,
            {
                "subject": notification_type.label,
                "cancelled_at": format_date(today(), locale=language),
                "lease": lease,
            },
            language=language,
        )
    except (AnymailError, OSError, ValidationError, VenepaikkaGraphQLError,) as e:
        # Flatten all the error messages on a single list
        errors = sum(e.message_dict.values(), [])
        raise VenepaikkaGraphQLError(errors)

    return lease
