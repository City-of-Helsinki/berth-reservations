import pytest

from applications.new_schema import BerthApplicationNode
from customers.schema import ProfileNode
from leases.schema import BerthLeaseNode
from resources.schema import BerthNode
from utils.relay import to_global_id

from ..schema.types import BerthSwitchOfferNode

BERTH_SWITCH_OFFERS_QUERY = """
query BERTH_SWITCH_OFFERS_QUERY  {
    berthSwitchOffers {
        edges {
            node {
                id
                customer {
                    id
                }
                application {
                    id
                }
                lease {
                    id
                }
                berth {
                    id
                }
            }
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_supervisor", "berth_handler", "berth_services"],
    indirect=True,
)
def test_get_berth_switch_offers(berth_switch_offer, api_client):
    executed = api_client.execute(BERTH_SWITCH_OFFERS_QUERY)

    assert len(executed["data"]["berthSwitchOffers"]["edges"]) == 1
    assert executed["data"]["berthSwitchOffers"]["edges"][0]["node"] == {
        "id": to_global_id(BerthSwitchOfferNode, berth_switch_offer.id),
        "customer": {"id": to_global_id(ProfileNode, berth_switch_offer.customer.id)},
        "application": {
            "id": to_global_id(BerthApplicationNode, berth_switch_offer.application.id)
        },
        "lease": {"id": to_global_id(BerthLeaseNode, berth_switch_offer.lease.id)},
        "berth": {"id": to_global_id(BerthNode, berth_switch_offer.berth.id)},
    }


BERTH_SWITCH_OFFER_QUERY = """
query BERTH_SWITCH_OFFER_QUERY  {
    berthSwitchOffer(id: "%s") {
        id
        customer {
            id
        }
        application {
            id
        }
        lease {
            id
        }
        berth {
            id
        }
    }
}
"""


@pytest.mark.parametrize(
    "api_client",
    ["berth_supervisor", "berth_handler", "berth_services"],
    indirect=True,
)
def test_get_berth_switch_offer(berth_switch_offer, api_client):
    offer_id = to_global_id(BerthSwitchOfferNode, berth_switch_offer.id)
    executed = api_client.execute(BERTH_SWITCH_OFFER_QUERY % offer_id)

    assert executed["data"]["berthSwitchOffer"] == {
        "id": offer_id,
        "customer": {"id": to_global_id(ProfileNode, berth_switch_offer.customer.id)},
        "application": {
            "id": to_global_id(BerthApplicationNode, berth_switch_offer.application.id)
        },
        "lease": {"id": to_global_id(BerthLeaseNode, berth_switch_offer.lease.id)},
        "berth": {"id": to_global_id(BerthNode, berth_switch_offer.berth.id)},
    }
