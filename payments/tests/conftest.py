import pytest
from factory.random import randgen

from berth_reservations.tests.conftest import *  # noqa
from payments.tests.factories import (
    AdditionalProductFactory,
    BerthProductFactory,
    WinterStorageProductFactory,
)
from resources.tests.conftest import *  # noqa
from resources.tests.factories import BerthTypeFactory


@pytest.fixture
def berth_price_group():
    # The BerthType (BT) save automatically creates a BerthPriceGroup (BPG) with the width
    # of the BT as name of the BPG. The BPG Factory assigns a random word as name, so, to avoid
    # hacky solutions, we instead create first the BT that are going to be assigned to the BPG
    # (all with the same width to have a single BPG) and then return the BPG associated to those BTs.
    width = randgen.uniform(1, 999)
    bt = BerthTypeFactory.create_batch(randgen.randint(1, 10), width=width)[0]

    berth_price_group = bt.price_group
    return berth_price_group


@pytest.fixture
def berth_product():
    berth_product = BerthProductFactory()
    return berth_product


@pytest.fixture
def winter_storage_product():
    winter_storage_product = WinterStorageProductFactory()
    return winter_storage_product


@pytest.fixture
def additional_product():
    additional_product = AdditionalProductFactory()
    return additional_product
