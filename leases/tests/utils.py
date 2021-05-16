from resources.models import Berth, WinterStorageArea


def create_berth_products(berth: Berth, create: bool = True):
    from payments.enums import PricingCategory
    from payments.tests.factories import BerthProductFactory

    strategy = "create" if create else "build"
    for pricing_category in PricingCategory.values:
        BerthProductFactory.generate(
            strategy=strategy,
            min_width=berth.berth_type.width - 1,
            max_width=berth.berth_type.width + 1,
            pricing_category=pricing_category,
        )


def create_winter_storage_product(area: WinterStorageArea, create: bool = True):
    from payments.tests.factories import WinterStorageProductFactory

    strategy = "create" if create else "build"
    WinterStorageProductFactory.generate(strategy=strategy, winter_storage_area=area)
