import pytest

from applications.schema import BerthApplicationNode
from berth_reservations.tests.utils import (
    assert_not_enough_permissions,
    create_api_client,
)
from customers.schema import ProfileNode
from leases.schema import BerthLeaseNode
from resources.schema import BerthNode
from utils.relay import to_global_id

from ..models import BerthSwitchOffer
from ..schema.types import BerthSwitchOfferNode
from .factories import BerthSwitchOfferFactory

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


@pytest.mark.parametrize(
    "api_client", ["api_client", "user", "harbor_services"], indirect=True,
)
def test_get_berth_switch_offers_not_enough_permissions(berth_switch_offer, api_client):
    executed = api_client.execute(BERTH_SWITCH_OFFERS_QUERY)
    assert_not_enough_permissions(executed)


def test_get_berth_switch_offers_by_owner(
    berth_customer_api_client, berth_switch_offer, customer_profile
):
    berth_switch_offer.customer.user = berth_customer_api_client.user
    berth_switch_offer.customer.save()

    executed = berth_customer_api_client.execute(BERTH_SWITCH_OFFERS_QUERY)

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


CUSTOMER_OWN_BERTH_SWITCH_OFFERS_QUERY = """
query ORDERS {
    berthSwitchOffers {
        edges {
            node {
                id
                lease {
                    customer {
                        id
                    }
                }
            }
        }
    }
}
"""


def test_get_customer_own_orders(customer_profile):
    customer_order = BerthSwitchOfferFactory(
        customer=customer_profile,
        lease__customer=customer_profile,
        application__customer=customer_profile,
    )
    BerthSwitchOfferFactory()

    api_client = create_api_client(user=customer_profile.user)
    executed = api_client.execute(CUSTOMER_OWN_BERTH_SWITCH_OFFERS_QUERY)

    assert BerthSwitchOffer.objects.count() == 2

    assert len(executed["data"]["berthSwitchOffers"]["edges"]) == 1
    assert executed["data"]["berthSwitchOffers"]["edges"][0]["node"] == {
        "id": to_global_id(BerthSwitchOfferNode, customer_order.id),
        "lease": {"customer": {"id": to_global_id(ProfileNode, customer_profile.id)}},
    }
