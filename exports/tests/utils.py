from typing import Type

from graphene_django import DjangoObjectType

from utils.relay import to_global_id


def to_global_ids(ids, object_type: Type[DjangoObjectType]):
    return map(lambda x: to_global_id(object_type, x), ids)
