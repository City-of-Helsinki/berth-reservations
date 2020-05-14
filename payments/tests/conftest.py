import pytest

from berth_reservations.tests.conftest import *  # noqa
from payments.tests.factories import (
    AdditionalProductFactory,
    BerthPriceGroupFactory,
    BerthProductFactory,
    WinterStorageProductFactory,
)


@pytest.fixture
def berth_price_group():
    berth_price_group = BerthPriceGroupFactory()
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
