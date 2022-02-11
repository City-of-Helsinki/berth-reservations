from typing import Type

from graphene_django import DjangoObjectType
from graphql_relay import from_global_id
from rest_framework import serializers


def from_global_ids(global_ids: [str], node_type: Type[DjangoObjectType]) -> [str]:
    return [_get_node_id_from_global_id(gid, node_type) for gid in global_ids]


def _get_node_id_from_global_id(
    global_id: str, node_type: Type[DjangoObjectType]
) -> str:
    try:
        name, id = from_global_id(global_id)
    except Exception:
        raise serializers.ValidationError("ID is not in correct format.")
    if name != node_type._meta.name:
        raise serializers.ValidationError("Node type does not match.")
    return id
