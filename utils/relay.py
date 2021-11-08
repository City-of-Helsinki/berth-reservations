from django.utils.translation import gettext_lazy as _
from graphene import relay
from graphql_jwt.exceptions import PermissionDenied
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


def get_node_user(node):
    if not node:
        return None

    node_user = None
    if hasattr(node, "user"):
        node_user = node.user
    elif hasattr(node, "owner") and hasattr(node.owner, "user"):
        node_user = node.owner.user
    elif hasattr(node, "customer") and hasattr(node.customer, "user"):
        node_user = node.customer.user
    return node_user


def user_is_linked_to_node(user, node):
    if user is None:
        return False
    return user == get_node_user(node)


def validate_user_is_linked_to_node(user, node):
    if not user_is_linked_to_node(user, node):
        raise PermissionDenied(_("You do not have permission to perform this action."))


def return_node_if_user_has_permissions(node, user, *models):
    """
    Checks whether the user has permissions to access this node / model.

    1. If the passed node is falsy, we return None.
    2. Otherwise, try to get the user this node belongs to (get_node_user)
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
    from users.utils import user_has_view_permission

    if not node:
        return None

    node_user = get_node_user(node)

    if (node_user and node_user == user) or user_has_view_permission(*models)(user):
        return node
    else:
        raise VenepaikkaGraphQLError(
            _("You do not have permission to perform this action.")
        )


def return_queryset_if_user_has_permissions(
    queryset, user, *models, customer_queryset=None
):
    """
    Checks whether the user has permissions to access the queryset.

    1. If the passed queryset is falsy, we return None.
    2. If the user making the request is a customer, the elements on the
        queryset belonging to it are returned.
    4. If the user is not a customer, but the user has permissions to view
        the necessary models, the whole queryset is returned.
    5. If the user has no permissions to view it, an error is raised.

    :param queryset: Django QuerySet being accessed
    :param user: the user from the current request / session
    :param models: Django models that user has to have permissions to
    :param customer_queryset: [Optional] If the customer property is nested on the model,
    a custom filtered queryset can be passed
    :return: None | Django QuerySet | Exception raised
    """
    from users.utils import is_customer, user_has_view_permission

    # First priority: an admin user OR a customer user with admin permissions
    if user_has_view_permission(*models)(user):
        return queryset

    # If the user doesn't have the equivalent to admin permissions,
    # check if it's a customer
    if is_customer(user):
        if customer_queryset is not None:
            # use customer_queryset even if it has no objects
            return customer_queryset
        return queryset.filter(customer__user=user)
    raise VenepaikkaGraphQLError(
        _("You do not have permission to perform this action.")
    )
