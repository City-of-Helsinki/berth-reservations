from decimal import Decimal as PythonDecimal

import pytest
from graphene import Decimal


@pytest.mark.parametrize(
    "value,expected", [(2.05, "2.05"), (5.3, "5.3"), (1, "1"), ("12.34", "12.34")]
)
def test_graphene_decimal_is_patched(value, expected):
    assert Decimal.parse_value(value) == PythonDecimal(expected)
