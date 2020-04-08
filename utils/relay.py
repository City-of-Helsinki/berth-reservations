from graphene import relay

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
