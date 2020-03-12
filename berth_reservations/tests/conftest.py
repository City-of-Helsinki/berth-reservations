import pytest

from .factories import CustomerProfileFactory, MunicipalityFactory, UserFactory
from .utils import create_api_client


@pytest.fixture(autouse=True)
def autouse_django_db(db):
    pass


@pytest.fixture(autouse=True)
def force_settings(settings):
    settings.MAILER_EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.DEFAULT_FROM_EMAIL = "noreply@foo.bar"
    settings.LANGUAGE_CODE = "en"


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def superuser():
    user = UserFactory(is_superuser=True)
    return user


@pytest.fixture
def user_api_client():
    return create_api_client(user=UserFactory())


@pytest.fixture
def staff_api_client():
    return create_api_client(user=UserFactory(is_staff=True))


@pytest.fixture
def superuser_api_client():
    return create_api_client(user=UserFactory(is_superuser=True))


@pytest.fixture
def api_client(request, user_api_client, staff_api_client, superuser_api_client):
    client_type = request.param if hasattr(request, "param") else None

    if client_type == "superuser_api_client":
        api_client = superuser_api_client
    elif client_type == "staff_api_client":
        api_client = staff_api_client
    elif client_type == "user_api_client":
        api_client = user_api_client

    # When the fixture is called without parameters, return the base api_client
    else:
        api_client = create_api_client()

    return api_client


@pytest.fixture
def old_schema_api_client():
    return create_api_client(graphql_v2=False)


@pytest.fixture
def municipality():
    municipality = MunicipalityFactory()
    return municipality


@pytest.fixture
def customer_profile():
    return CustomerProfileFactory()
