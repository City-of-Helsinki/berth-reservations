import pytest  # noqa

from payments.tests.factories import BerthProductFactory, WinterStorageProductFactory
from payments.utils import get_talpa_product_id
from resources.tests.factories import HarborFactory, WinterStorageAreaFactory


def test_berth_product_east():
    harbor = HarborFactory(region="east")
    berth_product = BerthProductFactory(harbor=harbor)
    assert (
        get_talpa_product_id(berth_product.id, harbor)
        == f"340100_2923301_2923301100_ _292015_44_{berth_product.id}"
    )


def test_berth_product_west():
    harbor = HarborFactory(region="west")
    berth_product = BerthProductFactory(harbor=harbor)
    assert (
        get_talpa_product_id(berth_product.id, harbor)
        == f"340100_2923302_2923302200_ _292015_44_{berth_product.id}"
    )


def test_berth_product_no_harbor():
    berth_product = BerthProductFactory(harbor=None)
    assert (
        get_talpa_product_id(berth_product.id, None)
        == f"340100_ _ _ _ _44_{berth_product.id}"
    )


def test_winter_storage_product_east():
    area = WinterStorageAreaFactory(region="east")
    winter_storage_product = WinterStorageProductFactory(winter_storage_area=area)
    assert (
        get_talpa_product_id(winter_storage_product.id, area)
        == f"340100_2923301_2923301100_ _292014_44_{winter_storage_product.id}"
    )


def test_winter_storage_product_west():
    area = WinterStorageAreaFactory(region="west")
    winter_storage_product = WinterStorageProductFactory(winter_storage_area=area)
    assert (
        get_talpa_product_id(winter_storage_product.id, area)
        == f"340100_2923302_2923302200_ _292014_44_{winter_storage_product.id}"
    )
