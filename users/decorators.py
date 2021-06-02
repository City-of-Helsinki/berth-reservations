from functools import wraps
from typing import Callable, List, Optional

from graphql_jwt.decorators import permission_required, user_passes_test
from graphql_jwt.exceptions import PermissionDenied

from .utils import is_customer, user_has_models_perms, user_is_linked_to_node


def view_permission_required(*models):
    """Decorator to validate the request user has VIEW permissions for the models provided"""
    return user_passes_test(user_has_models_perms("view", models))


def add_permission_required(*models):
    """Decorator to validate the request user has ADD permissions for the models provided"""
    return user_passes_test(user_has_models_perms("add", models))


def change_permission_required(*models):
    """Decorator to validate the request user has CHANGE (edit) permissions for the models provided"""
    return user_passes_test(user_has_models_perms("change", models))


def delete_permission_required(*models):
    """Decorator to validate the request user has DELETE permissions for the models provided"""
    return user_passes_test(user_has_models_perms("delete", models))


def check_user_is_authorised(
    get_nodes_to_check: Optional[Callable] = None,
    model_checks: Optional[List[Callable]] = None,
):
    """
    Decorator for use with mutate_and_get_payload()
    If the context.user is a customer, it checks that the user is owner of the provided nodes
    If the context.user is an user, we assume it's an admin and we check that it has the permissions
    for the models listed on models_check

    :param get_nodes_to_check: Callable that returns the nodes to be checked for the user
    :param model_checks: List of callables that will be executed to check for permissions
    :return:
    """
    if model_checks is None:
        model_checks = []

    def decorator(f):
        @wraps(f)
        def wrapper(cls, root, info, **input):
            nodes_to_check = (
                get_nodes_to_check(info, **input) if get_nodes_to_check else []
            )
            user = info.context.user

            if (
                is_customer(user)
                and all([user_is_linked_to_node(user, node) for node in nodes_to_check])
            ) or all([check(user) for check in model_checks]):
                return f(cls, root, info, **input)
            raise PermissionDenied

        return wrapper

    return decorator


def custom_permissions_required(*perms):
    """Decorator to validate the request user has custom permissions (defined on a model basis)"""
    return permission_required(perms)
