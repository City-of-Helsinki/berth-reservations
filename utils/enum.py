from graphene import Enum


def graphene_enum(enum):
    return Enum.from_enum(enum, description=lambda e: e.label if e else "")
