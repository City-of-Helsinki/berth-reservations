from graphql_jwt.decorators import permission_required, user_passes_test

from .utils import _user_has_models_perms


def view_permission_required(*models):
    """Decorator to validate the request user has VIEW permissions for the models provided"""
    return user_passes_test(_user_has_models_perms("view", models))


def add_permission_required(*models):
    """Decorator to validate the request user has ADD permissions for the models provided"""
    return user_passes_test(_user_has_models_perms("add", models))


def change_permission_required(*models):
    """Decorator to validate the request user has CHANGE (edit) permissions for the models provided"""
    return user_passes_test(_user_has_models_perms("change", models))


def delete_permission_required(*models):
    """Decorator to validate the request user has DELETE permissions for the models provided"""
    return user_passes_test(_user_has_models_perms("delete", models))


def custom_permissions_required(*perms):
    """Decorator to validate the request user has custom permissions (defined on a model basis)"""
    return permission_required(perms)
