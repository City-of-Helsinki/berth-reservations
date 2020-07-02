from graphene import relay
from graphql_relay import (
    from_global_id as relay_from_global_id,
    to_global_id as relay_to_global_id,
)

from berth_reservations.exceptions import VenepaikkaGraphQLError


def get_node_from_global_id(info, global_id, only_type, nullable=True):
    """
    Utilise relay's get_node_from_global_id to handle errors decoding invalid global ids.
    Returns the instance found or raises an error if none was found (also the case if the ID is invalid)

    The nullable allows to explicitly ignore the DoesNotExist error and return None instead. This helps
    hide information that shouldn't be returned to the client. The default value is True for tighter security.
    """
    instance = relay.Node.get_node_from_global_id(info, global_id, only_type=only_type)
    model = only_type._meta.model

    if not instance and not nullable:
        raise VenepaikkaGraphQLError(
            model.DoesNotExist(
                f"{model._meta.object_name} matching query does not exist."
            )
        )

    return instance


def to_global_id(node_type, id):
    """
    Wrapper around the graphql_relay to_global_id.

    Takes a graphql type and an ID specific to that type name, and returns a
    "global ID" that is unique among all types.

    Instead of expecting the type name, it takes the full type and tries to
    get the name to reduce code repetition.
    """
    return relay_to_global_id(node_type._meta.name, str(id))


def from_global_id(global_id, node_type=None):
    """
    Wrapper around the graphql_relay from_global_id.

    Takes the "global ID" created by toGlobalID and optionally the expected NodeType.
    If no NodeType is passed, it will only return the decoded id.
    If NodeType is passed, it will assert that the decoded id belongs to that NodeType.
    """
    _type, _id = relay_from_global_id(global_id)
    if node_type:
        assert (
            _type == node_type._meta.name
        ), f"Must receive a {node_type._meta.name} id."
    return _id
