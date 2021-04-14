from typing import Optional

from django.utils.translation import gettext_lazy as _

from berth_reservations.exceptions import VenepaikkaGraphQLError
from customers.models import Boat
from resources.models import BoatType
from utils.relay import get_node_from_global_id, to_global_id


def parse_invoicing_result(node_type):
    """Wrapper function to allow reusing the parse function with different Node types"""

    def parse_to_dict(object):
        """Util function to parse a dict of {"UUID": "message"} into {"id": "UUID", "error": "message"} """
        id, error = list(object.items())[0]
        return {"id": to_global_id(node_type, id), "error": error}

    return parse_to_dict


def lookup_or_create_boat(info, input: dict) -> Optional[Boat]:
    boat: Optional[Boat] = None

    if input.get("boat_id"):
        from customers.schema import BoatNode

        boat = get_node_from_global_id(
            info, input.pop("boat_id"), only_type=BoatNode, nullable=False,
        )

        if boat.owner.id != input["customer"].id:
            raise VenepaikkaGraphQLError(
                _("Boat does not belong to the same customer as the Application")
            )
    elif application := input.get("application"):
        # TODO: Remove this mapping
        # This will only be done until the Harbors app is removed.
        # The boat types are loaded from a fixture and they have the same ID and translations,
        # so this is a safe temporary solution
        boat_type = BoatType.objects.get(id=application.boat_type_id,)

        boat_input = {
            "boat_type": boat_type,
            "name": application.boat_name,
            "model": application.boat_model,
            "length": application.boat_length,
            "width": application.boat_width,
            "draught": getattr(application, "boat_draught", None),
            "weight": getattr(application, "boat_weight", None),
            "propulsion": getattr(application, "boat_propulsion", ""),
            "hull_material": getattr(application, "boat_hull_material", ""),
            "intended_use": getattr(application, "boat_intended_use", ""),
        }
        boat, _created = Boat.objects.update_or_create(
            owner=application.customer,
            registration_number=application.boat_registration_number,
            defaults=boat_input,
        )
    return boat
