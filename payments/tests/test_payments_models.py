import random
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from payments.enums import AdditionalProductType, PeriodType, PriceUnits, ServiceType
from payments.models import DEFAULT_TAX_PERCENTAGE
from payments.tests.factories import (
    AdditionalProductFactory,
    BerthProductFactory,
    WinterStorageProductFactory,
)


def test_berth_product_invalid_price_unit():
    with pytest.raises(ValidationError) as exception:
        BerthProductFactory(price_unit=PriceUnits.PERCENTAGE)

    errors = str(exception.value)
    assert "percentage" in errors
    assert "is not a valid choice" in errors


def test_berth_product_invalid_tax():
    with pytest.raises(ValidationError) as exception:
        BerthProductFactory(tax_percentage=Decimal("10.00"))

    errors = str(exception.value)
    assert "tax_percentage" in errors
    assert "is not a valid choice" in errors


def test_winter_storage_product_invalid_price_unit():
    with pytest.raises(ValidationError) as exception:
        WinterStorageProductFactory(price_unit=PriceUnits.PERCENTAGE)

    errors = str(exception.value)
    assert "percentage" in errors
    assert "is not a valid choice" in errors


def test_winter_storage_product_invalid_tax():
    with pytest.raises(ValidationError) as exception:
        WinterStorageProductFactory(tax_percentage=Decimal("10.00"))

    errors = str(exception.value)
    assert "tax_percentage" in errors
    assert "is not a valid choice" in errors


def test_additional_product_product_type_fixed():
    product = AdditionalProductFactory(
        service=ServiceType.ELECTRICITY,
        tax_percentage=DEFAULT_TAX_PERCENTAGE,
        period=PeriodType.SEASON,
    )
    assert product.product_type == AdditionalProductType.FIXED_SERVICE


def test_additional_product_product_type_optional():
    product = AdditionalProductFactory(service=ServiceType.DINGHY_PLACE)
    assert product.product_type == AdditionalProductType.OPTIONAL_SERVICE


def test_additional_product_one_service_per_period():
    service = random.choice(ServiceType.OPTIONAL_SERVICES())
    period = random.choice(list(PeriodType))

    AdditionalProductFactory(service=service, period=period)

    with pytest.raises(IntegrityError) as exception:
        AdditionalProductFactory(service=service, period=period)

    errors = str(exception.value)
    assert (
        'duplicate key value violates unique constraint "optional_services_per_period"'
        in errors
    )


@pytest.mark.parametrize("period", [PeriodType.MONTH, PeriodType.YEAR])
def test_additional_product_no_season(period):
    with pytest.raises(ValidationError) as exception:
        AdditionalProductFactory(
            service=ServiceType.ELECTRICITY,
            tax_percentage=DEFAULT_TAX_PERCENTAGE,
            period=period,
        )

    errors = str(exception.value)
    assert f"Fixed services are only valid for season" in errors


def test_additional_product_fixed_service_tax_value():
    with pytest.raises(ValidationError) as exception:
        AdditionalProductFactory(
            service=random.choice(ServiceType.FIXED_SERVICES()),
            tax_percentage=Decimal("10.00"),
        )

    errors = str(exception.value)
    assert f"Fixed services must have VAT of {DEFAULT_TAX_PERCENTAGE}€" in errors
