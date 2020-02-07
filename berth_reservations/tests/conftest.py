import pytest

from .factories import CustomerProfileFactory, MunicipalityFactory, UserFactory


@pytest.fixture(autouse=True)
def autouse_django_db(db):
    pass


@pytest.fixture(autouse=True)
def force_settings(settings):
    settings.MAILER_EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.DEFAULT_FROM_EMAIL = "noreply@foo.bar"
    settings.LANGUAGE_CODE = "en"


@pytest.fixture
def user(request):
    permissions = request.param if hasattr(request, "param") else None

    if permissions == "superuser":
        user = UserFactory(is_superuser=True)
    elif permissions == "staff":
        user = UserFactory(is_staff=True)
    elif permissions == "none":
        user = None
    # When the fixture is called without parameters, return the base user
    elif permissions == "base" or permissions is None:
        user = UserFactory()

    return user


@pytest.fixture
def superuser():
    user = UserFactory(is_superuser=True)
    return user


@pytest.fixture
def municipality():
    municipality = MunicipalityFactory()
    return municipality


@pytest.fixture
def customer_profile():
    return CustomerProfileFactory()
