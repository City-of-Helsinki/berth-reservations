from decimal import Decimal as _Decimal

import graphene
from graphene.types import Decimal


def monkeypatch_graphene_decimal():
    if graphene.__version__ != "2.1.9":
        raise Exception(
            "Graphene version changed. Check if graphene.Decimal still needs patching."
        )

    def parse_value(value):
        try:
            # Turn value to string first to handle possible floats gracefully.
            return _Decimal(str(value))
        except ValueError:
            return None

    Decimal.parse_value = parse_value
