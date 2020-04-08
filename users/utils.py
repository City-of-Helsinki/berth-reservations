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
