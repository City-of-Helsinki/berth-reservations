import pytest

from customers.models import User

from ..utils import _build_permstring, _user_has_models_perms


@pytest.mark.parametrize(
    "perm,model,expected",
    (("view", User, "users.view_user"), ("create", User, "users.create_user")),
)
def test_build_permstring(perm, model, expected):
    assert _build_permstring(perm, model) == expected


def test_user_has_models_perms():
    wrapper = _user_has_models_perms("view", (User,))
    assert wrapper is not None


def test_user_has_models_perms_no_models():
    with pytest.raises(ValueError) as exception:
        _user_has_models_perms("view", tuple())

    assert exception.value.args[0] == "Please provide at least one model"


def test_user_has_models_perms_invalid_perm():
    with pytest.raises(ValueError) as exception:
        _user_has_models_perms("foobar", (User,))

    assert exception.value.args[0] == "The permission to check is not a valid type"
