import pytest

from notifications.enums import NotificationType
from notifications.models import (
    NotificationTemplate, NotificationTemplateException
)
from notifications.utils import render_notification_template


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


def test_notification_template_rendering(notification_template):
    context = {
        'extra_var': 'foo',
        'subject_var': 'bar',
        'html_body_var': 'html_baz',
        'text_body_var': 'text_baz',
    }

    rendered = render_notification_template(NotificationType.RESERVATION_CREATED, context, 'en')
    assert len(rendered) == 3
    assert rendered.subject == "test subject, variable value: bar!"
    assert rendered.html_body == "<b>test html body</b>, variable value: html_baz!"
    assert rendered.text_body == "test text body, variable value: text_baz!"

    rendered = render_notification_template(NotificationType.RESERVATION_CREATED, context, 'fi')
    assert len(rendered) == 3
    assert rendered.subject == "testiotsikko, muuttujan arvo: bar!"
    assert rendered.html_body == "<b>testihötömölöruumis</b>, muuttujan arvo: html_baz!"
    assert rendered.text_body == "testitekstiruumis, muuttujan arvo: text_baz!"


def test_notification_template_rendering_no_text_body_provided(notification_template):
    context = {
        'extra_var': 'foo',
        'subject_var': 'bar',
        'html_body_var': 'html_baz',
        'text_body_var': 'text_baz',
    }
    notification_template.set_current_language('fi')
    notification_template.text_body = ''
    notification_template.save()
    notification_template.set_current_language('en')
    notification_template.text_body = ''
    notification_template.save()

    rendered = render_notification_template(NotificationType.RESERVATION_CREATED, context, 'en')
    assert len(rendered) == 3
    assert rendered.subject == "test subject, variable value: bar!"
    assert rendered.html_body == "<b>test html body</b>, variable value: html_baz!"
    assert rendered.text_body == "test html body, variable value: html_baz!"

    rendered = render_notification_template(NotificationType.RESERVATION_CREATED, context, 'fi')
    assert len(rendered) == 3
    assert rendered.subject == "testiotsikko, muuttujan arvo: bar!"
    assert rendered.html_body == "<b>testihötömölöruumis</b>, muuttujan arvo: html_baz!"
    assert rendered.text_body == "testihötömölöruumis, muuttujan arvo: html_baz!"


def test_undefined_rendering_context_variable(notification_template):
    context = {
        'extra_var': 'foo',
        'subject_var': 'bar',
        'text_body_var': 'baz',
    }

    with pytest.raises(NotificationTemplateException) as e:
        render_notification_template(NotificationType.RESERVATION_CREATED, context, 'fi')
    assert "'html_body_var' is undefined" in str(e)
