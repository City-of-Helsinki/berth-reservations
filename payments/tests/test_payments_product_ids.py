import pytest  # noqa

from payments.tests.factories import (
    AdditionalProductFactory,
    BerthProductFactory,
    WinterStorageProductFactory,
)
from payments.utils import get_talpa_product_id
from resources.tests.factories import HarborFactory, WinterStorageAreaFactory


@pytest.mark.parametrize(
    "region,business_unit,internal_order",
    [("east", "2923301", "2923301100"), ("west", "2923302", "2923302200")],
)
def test_berth_product(customer_profile, region, business_unit, internal_order):
    harbor = HarborFactory(region=region)
    product = BerthProductFactory()
    assert (
        get_talpa_product_id(product.id, harbor)
        == f"340100_{business_unit}_{internal_order}_ _292015_44_{product.id}"
    )


@pytest.mark.parametrize(
    "region,business_unit,internal_order",
    [("east", "2923301", "2923301100"), ("west", "2923302", "2923302200")],
)
def test_winter_storage_product(
    customer_profile, region, business_unit, internal_order
):
    area = WinterStorageAreaFactory(region=region)
    product = WinterStorageProductFactory(winter_storage_area=area)
    assert (
        get_talpa_product_id(product.id, area)
        == f"340100_{business_unit}_{internal_order}_ _292014_44_{product.id}"
    )


@pytest.mark.parametrize(
    "region,business_unit,internal_order",
    [("east", "2923301", "2923301100"), ("west", "2923302", "2923302200")],
)
def test_storage_on_ice(customer_profile, region, business_unit, internal_order):
    harbor = HarborFactory(region=region)
    product = AdditionalProductFactory()
    assert (
        get_talpa_product_id(product.id, harbor, True)
        == f"340100_{business_unit}_{internal_order}_ _292014_44_{product.id}"
    )
