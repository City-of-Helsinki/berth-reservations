from functools import lru_cache

from django.conf import settings
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from graphql_jwt.exceptions import PermissionDenied

VALID_PERMS = ["view", "add", "change", "delete"]


def _build_permstring(perm, model):
    """
    Return the full permission string for a given permission and model
    The perm strings follow the format <app_label>.<permission>_<model_name>
    """
    return f"{model._meta.app_label}.{perm}_{model._meta.model_name}"


def _user_has_models_perms(perm, models):
    """Check if the user has all the permissions required"""
    if len(list(models)) == 0:
        raise ValueError("Please provide at least one model")

    if perm not in VALID_PERMS:
        raise ValueError("The permission to check is not a valid type")

    def wrapper(user):
        return user.has_perms([_build_permstring(perm, model) for model in models])

    return wrapper


def user_has_view_permission(user, *models):
    return _user_has_models_perms("view", models)(user)


def user_has_add_permission(user, *models):
    return _user_has_models_perms("add", models)(user)


def user_has_change_permission(user, *models):
    return _user_has_models_perms("change", models)(user)


def user_has_delete_permission(user, *models):
    return _user_has_models_perms("delete", models)(user)


def is_customer(user):
    if user.is_staff or user.is_superuser:
        return False
    elif (
        user.groups.count() == 1
        and user.groups.first().name == settings.CUSTOMER_GROUP_NAME
    ):
        return True
    return False


@lru_cache(maxsize=3)
def get_berth_customers_group() -> Group:
    return Group.objects.get(name=settings.CUSTOMER_GROUP_NAME)


def get_node_user(node):
    """
       Try to get to the user this node belongs to
       either directly by node.user or through CustomerProfile,
       i.e. by doing node.customer.user
    """
    if not node:
        return None

    node_user = None
    if hasattr(node, "user"):
        node_user = node.user
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
