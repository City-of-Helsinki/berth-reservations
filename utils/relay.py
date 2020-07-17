from django.utils.translation import ugettext_lazy as _
from graphene import relay
from graphql_relay import (
    from_global_id as relay_from_global_id,
    to_global_id as relay_to_global_id,
)

from berth_reservations.exceptions import VenepaikkaGraphQLError
from users.utils import user_has_view_permission


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


def return_node_if_user_has_permissions(node, user, *models):
    """
    Checks whether the user has permissions to access this node / model.

    1. If the passed node is falsy, we return None.
    2. Otherwise we try to get to the user this node belongs to,
       either directly by node.user or through CustomerProfile,
       i.e. by doing node.customer.user
    3. If the node belongs to the user making the request,
       the node / model is returned.
    4. If the node does not belong to the user, but the user has
       permissions to view the necessary models, the node / model
       is still returned.
    5. If the node does not belong to the user and the user has no
       permissions to view it, an error is raised.

    :param node: Graphene Node or Django Model being accessed
    :param user: the user from the current request / session
    :param models: Django models that user has to have permissions to
    :return: None | Django Model or Graphene Node | Exception raised
    """
    if not node:
        return None

    node_user = None
    if hasattr(node, "user"):
        node_user = node.user
    elif hasattr(node, "customer") and hasattr(node.customer, "user"):
        node_user = node.customer.user

    if (node_user and node_user == user) or user_has_view_permission(user, *models):
        return node
    else:
        raise VenepaikkaGraphQLError(
            _("You do not have permission to perform this action.")
        )
