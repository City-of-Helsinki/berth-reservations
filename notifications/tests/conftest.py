import pytest

from berth_reservations.tests.conftest import *  # noqa

from ..enums import NotificationType
from ..models import NotificationTemplate


@pytest.fixture(autouse=True)
def email_setup(settings):
    settings.EMAIL_BACKEND = 'mailer.backend.DbBackend'
    settings.NOTIFICATIONS_ENABLED = True


@pytest.fixture
def notification_template(settings):
    settings.LANGUAGES = (('fi', 'Finnish'), ('en', 'English'))

    template = NotificationTemplate.objects.language('en').create(
        type=NotificationType.RESERVATION_CREATED,
        subject="test subject, variable value: {{ subject_var }}!",
        html_body="<b>test html body</b>, variable value: {{ html_body_var }}!",
        text_body="test text body, variable value: {{ text_body_var }}!",

    )
    template.set_current_language('fi')
    template.subject = "testiotsikko, muuttujan arvo: {{ subject_var }}!"
    template.html_body = "<b>testihötömölöruumis</b>, muuttujan arvo: {{ html_body_var }}!"
    template.text_body = "testitekstiruumis, muuttujan arvo: {{ text_body_var }}!"

    template.save()

    return template


@pytest.fixture
def dummy_context():
    return {
        'extra_var': 'foo',
        'subject_var': 'bar',
        'html_body_var': 'html_baz',
        'text_body_var': 'text_baz',
    }
