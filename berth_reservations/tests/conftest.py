from os.path import devnull

import pytest
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management import call_command
from django_ilmoitin.models import NotificationTemplate

from contracts.tests.utils import TestContractService
from customers.enums import OrganizationType
from customers.tests.factories import OrganizationFactory

from .factories import CustomerProfileFactory, MunicipalityFactory, UserFactory
from .utils import create_api_client


@pytest.fixture(autouse=True)
def autouse_django_db(db, django_db_setup, django_db_blocker):
    pass


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command("loaddata", "groups.json")
        with open(devnull, "a") as null:
            call_command("set_group_model_permissions", stdout=null, stderr=null)


@pytest.fixture(scope="session")
def django_db_modify_db_settings():
    pass


@pytest.fixture(autouse=True)
def force_settings(settings):
    settings.MAILER_EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.DEFAULT_FROM_EMAIL = "noreply@foo.bar"
    settings.LANGUAGE_CODE = "en"
    settings.VENE_UI_RETURN_URL = "https://front-end-url/{LANG}"
    settings.NOTIFICATION_SERVICE_TOKEN = "fake_token"


@pytest.fixture
def user_api_client():
    return create_api_client(user=UserFactory())


@pytest.fixture
def superuser_api_client():
    return create_api_client(user=UserFactory(is_superuser=True))


@pytest.fixture
def berth_services_api_client():
    user = UserFactory()
    group = Group.objects.get(name="Berth services")
    user.groups.set([group])
    return create_api_client(user=user)


@pytest.fixture
def berth_supervisor_api_client():
    user = UserFactory()
    group = Group.objects.get(name="Berth supervisor")
    user.groups.set([group])
    return create_api_client(user=user)


@pytest.fixture
def berth_handler_api_client():
    user = UserFactory()
    group = Group.objects.get(name="Berth handler")
    user.groups.set([group])
    return create_api_client(user=user)


@pytest.fixture
def harbor_services_api_client():
    user = UserFactory()
    group = Group.objects.get(name="Harbour services")
    user.groups.set([group])
    return create_api_client(user=user)


@pytest.fixture
def berth_customer_user():
    user = UserFactory()
    group = Group.objects.get(name="Berth customer")
    user.groups.set([group])
    return user


@pytest.fixture
def berth_customer_api_client():
    user = UserFactory()
    group = Group.objects.get(name="Berth customer")
    user.groups.set([group])
    return create_api_client(user=user)


@pytest.fixture
def berth_customer_weak_auth_api_client():
    user = UserFactory()
    group = Group.objects.get(name="Berth customer")
    user.groups.set([group])
    return create_api_client(user=user, strong_auth=False)


@pytest.fixture
def api_client(
    request,
    user_api_client,
    berth_services_api_client,
    berth_supervisor_api_client,
    berth_handler_api_client,
    harbor_services_api_client,
):
    client_type = request.param if hasattr(request, "param") else None

    if client_type == "berth_services":
        api_client = berth_services_api_client
    elif client_type == "berth_supervisor":
        api_client = berth_supervisor_api_client
    elif client_type == "berth_handler":
        api_client = berth_handler_api_client
    elif client_type == "harbor_services":
        api_client = harbor_services_api_client
    elif client_type == "user":
        api_client = user_api_client

    # When the fixture is called without parameters, return the base api_client
    else:
        api_client = create_api_client()

    return api_client


@pytest.fixture
def municipality():
    municipality = MunicipalityFactory()
    return municipality


@pytest.fixture
def customer_profile():
    profile = CustomerProfileFactory()
    group, _created = Group.objects.get_or_create(name=settings.CUSTOMER_GROUP_NAME)
    profile.user.groups.set([group])
    return profile


@pytest.fixture
def company_customer(customer_profile):
    OrganizationFactory(
        customer=customer_profile, organization_type=OrganizationType.COMPANY
    )
    return customer_profile


@pytest.fixture
def non_billable_customer(customer_profile):
    OrganizationFactory(
        customer=customer_profile, organization_type=OrganizationType.NON_BILLABLE
    )
    return customer_profile


@pytest.fixture
def notification_template_orders_approved():
    from payments.notifications import NotificationType

    for value in NotificationType.values:
        if not value.startswith("sms"):
            notification = NotificationTemplate.objects.language("fi").create(
                type=value,
                subject="test order approved subject, event: {{ order.order_number }}!",
                body_html="<b>{{ order.order_number }} {{ payment_url }}</b>",
                body_text="{{ order.order_number }} {{ payment_url }}",
            )
            notification.create_translation(
                "en",
                subject="test order approved subject, event: {{ order.order_number }}!",
                body_html="<b>{{ order.order_number }} {{ payment_url }}</b>",
                body_text="{{ order.order_number }} {{ payment_url }}",
            )

    NotificationTemplate.objects.language("fi").create(
        type=NotificationType.SMS_INVOICE_NOTICE.value,
        subject="SMS invoice notice",
        body_html="Remember to pay your invoice {{ product_name }} by {{ due_date }}",
        body_text="Remember to pay your invoice {{ product_name }} by {{ due_date }}",
    )


@pytest.fixture
def notification_template_order_cancelled():
    from payments.notifications import NotificationType

    for value in NotificationType.values:
        notification = NotificationTemplate.objects.language("fi").create(
            type=value,
            subject="test order cancelled subject: {{ order.order_number }}!",
            body_html="<b>{{ order.order_number }} {{ rejected_at }}</b>",
            body_text="{{ order.order_number }} {{ rejected_at }}",
        )
        notification.create_translation(
            "en",
            subject="test order cancelled subject: {{ order.order_number }}!",
            body_html="<b>{{ order.order_number }} {{ rejected_at }}</b>",
            body_text="{{ order.order_number }} {{ rejected_at }}",
        )


@pytest.fixture
def notification_template_order_refunded():
    from payments.notifications import NotificationType

    notification = NotificationTemplate.objects.language("fi").create(
        type=NotificationType.ORDER_REFUNDED,
        subject="test order refunded subject: {{ order.order_number }}!",
        body_html="<b>{{ order.order_number }} {{ order.price }}</b>",
        body_text="{{ order.order_number }} {{ order.price }}",
    )
    notification.create_translation(
        "en",
        subject="test order refunded subject: {{ order.order_number }}!",
        body_html="<b>{{ order.order_number }} {{ order.price }}</b>",
        body_text="{{ order.order_number }} {{ order.price }}",
    )
    return notification


@pytest.fixture
def notification_template_switch_offer_sent():
    from payments.notifications import NotificationType

    notification = NotificationTemplate.objects.language("fi").create(
        type=NotificationType.BERTH_SWITCH_OFFER_APPROVED,
        subject="test offer sent subject, event: {{ offer.pk }}!",
        body_html="<b>{{ offer.pk }} {{ accept_url }}</b>",
        body_text="{{ offer.pk }} {{ accept_url }}",
    )
    notification.create_translation(
        "en",
        subject="test offer sent subject, event: {{ offer.pk }}!",
        body_html="<b>{{ offer.pk }} {{ accept_url }}</b>",
        body_text="{{ offer.pk }} {{ accept_url }}",
    )
    NotificationTemplate.objects.language("fi").create(
        type=NotificationType.SMS_BERTH_SWITCH_NOTICE.value,
        subject="SMS offer notice",
        body_html="Offer {{ offer.pk }} due date {{ due_date }}",
        body_text="Offer {{ offer.pk }} due date {{ due_date }}",
    )
    return notification


@pytest.fixture(autouse=True)
def patch_contract_service(monkeypatch):
    monkeypatch.setattr(
        "contracts.services.VismaContractService", lambda: TestContractService()
    )
