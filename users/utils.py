from functools import lru_cache

from django.conf import settings
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from graphql_jwt.exceptions import PermissionDenied

from utils.relay import get_node_user

VALID_PERMS = ["view", "add", "change", "delete"]


def _build_permstring(perm, model):
    """
    Return the full permission string for a given permission and model
    The perm strings follow the format <app_label>.<permission>_<model_name>
    """
    return f"{model._meta.app_label}.{perm}_{model._meta.model_name}"


def user_has_models_perms(perm, models):
    """Check if the user has all the permissions required"""
    if len(list(models)) == 0:
        raise ValueError("Please provide at least one model")

    if perm not in VALID_PERMS:
        raise ValueError("The permission to check is not a valid type")

    def wrapper(user):
        return user.has_perms([_build_permstring(perm, model) for model in models])

    return wrapper


def user_has_view_permission(*models):
    return user_has_models_perms("view", models)


def user_has_add_permission(*models):
    return user_has_models_perms("add", models)


def user_has_change_permission(*models):
    return user_has_models_perms("change", models)


def user_has_delete_permission(*models):
    return user_has_models_perms("delete", models)


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


def user_is_linked_to_node(user, node):
    if user is None:
        return False
    return user == get_node_user(node)


def validate_user_is_linked_to_node(user, node):
    if not user_is_linked_to_node(user, node):
        raise PermissionDenied(_("You do not have permission to perform this action."))
