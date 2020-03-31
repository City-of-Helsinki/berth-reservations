from graphene import relay

from berth_reservations.exceptions import VenepaikkaGraphQLError


def get_node_from_global_id(info, global_id, only_type):
    """
    Utilise relay's get_node_from_global_id to handle errors decoding invalid global ids.
    Returns the instance found or raises an error if none was found (also the case if the ID is invalid)
    """
    instance = relay.Node.get_node_from_global_id(info, global_id, only_type=only_type)
    model = only_type._meta.model

    if not instance:
        raise VenepaikkaGraphQLError(
            model.DoesNotExist(
                f"{model._meta.object_name} matching query does not exist."
            )
        )

    return instance
