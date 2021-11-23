from typing import Optional

from django.utils.translation import gettext_lazy as _

from berth_reservations.exceptions import VenepaikkaGraphQLError
from customers.models import Boat
from utils.relay import get_node_from_global_id, to_global_id


def parse_invoicing_result(node_type):
    """Wrapper function to allow reusing the parse function with different Node types"""

    def parse_to_dict(object):
        """Util function to parse a dict of {"UUID": "message"} into {"id": "UUID", "error": "message"}"""
        id, error = list(object.items())[0]
        return {"id": to_global_id(node_type, id), "error": error}

    return parse_to_dict


def lookup_or_create_boat(info, input: dict) -> Optional[Boat]:
    boat: Optional[Boat] = None

    if input.get("boat_id"):
        from customers.schema import BoatNode

        boat = get_node_from_global_id(
            info,
            input.pop("boat_id"),
            only_type=BoatNode,
            nullable=False,
        )

        if boat.owner.id != input["customer"].id:
            raise VenepaikkaGraphQLError(
                _("Boat does not belong to the same customer as the Application")
            )
    elif application := input.get("application"):
        boat = application.boat
    return boat
