import logging
from collections import namedtuple

from django.conf import settings
from django.core.mail import send_mail as django_send_mail
from django.utils.html import strip_tags
from jinja2 import StrictUndefined
from jinja2.exceptions import TemplateError
from jinja2.sandbox import SandboxedEnvironment
from parler.utils.context import switch_language

from notifications.models import NotificationTemplate, NotificationTemplateException

logger = logging.getLogger(__name__)

DEFAULT_LANGUAGE = settings.LANGUAGES[0][0]

RenderedTemplate = namedtuple('RenderedTemplate', ('subject', 'html_body', 'text_body'))


def send_notification(email, notification_type, context=None, language=DEFAULT_LANGUAGE):
    logger.debug('Trying to send notification "{}" to {}.'.format(notification_type, email))

    if context is None:
        context = {}

    try:
        subject, html_body, text_body = render_notification_template(notification_type, context, language)
    except NotificationTemplate.DoesNotExist:
        logger.debug('NotificationTemplate "{}" does not exist, not sending anything.'.format(notification_type))
        return
    except NotificationTemplateException as e:
        logger.error(e, exc_info=True, extra={'user_email': email})
        return

    if not subject:
        logger.warning(
            'Rendered notification "{}" has an empty subject, not sending anything.'.format(notification_type)
        )
        return

    if not html_body:
        logger.warning(
            'Rendered notification "{}" has an empty body, not sending anything.'.format(notification_type)
        )
        return

    send_mail(subject, html_body, text_body, email)


def render_notification_template(notification_type, context, language_code=DEFAULT_LANGUAGE):
    """
    Render a notification template with given context in given language

    Returns a namedtuple containing all content fields (subject, html_body, text_body) of the template.
    """
    template = NotificationTemplate.objects.get(type=notification_type)
    env = SandboxedEnvironment(trim_blocks=True, lstrip_blocks=True, undefined=StrictUndefined)

    with switch_language(template, language_code):
        try:
            subject = env.from_string(template.subject).render(context)
            html_body = env.from_string(template.html_body).render(context)

            if template.text_body:
                text_body = env.from_string(template.text_body).render(context)
            else:
                text_body = strip_tags(html_body)

            return RenderedTemplate(subject, html_body, text_body)

        except TemplateError as e:
            raise NotificationTemplateException(e) from e


def send_mail(subject, html_body, text_body, to_address):
    logger.info('Sending notification email to {}: "{}"'.format(to_address, subject))
    django_send_mail(subject, text_body, settings.DEFAULT_FROM_EMAIL, [to_address], html_message=html_body)
