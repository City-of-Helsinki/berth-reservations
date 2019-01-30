from unittest import mock

from django.conf import settings
from django.core import mail
from mailer.models import (
    Message, MessageLog, PRIORITY_DEFERRED, RESULT_FAILURE, RESULT_SUCCESS
)
from raven import Client

from ..utils import send_notification


def test_mailer_fired_automatically(notification_template, dummy_context):
    assert not Message.objects.exists()
    assert not MessageLog.objects.exists()

    # Ensure mailer will fail as SMTP is not configured
    settings.MAILER_EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    # Mailer will attempt to send the message but it will be deferred
    send_notification(
        'receiver@example.com', notification_template.type, dummy_context)

    assert Message.objects.filter(priority=PRIORITY_DEFERRED).count() == 1
    assert MessageLog.objects.filter(result=RESULT_FAILURE).count() == 1

    # Now messages will be sent successfully
    settings.MAILER_EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    send_notification(
        'receiver@example.com', notification_template.type, dummy_context)

    assert Message.objects.filter(priority=PRIORITY_DEFERRED).count() == 0
    assert MessageLog.objects.filter(result=RESULT_SUCCESS).count() == 2


@mock.patch('notifications.signals.MailerFailureException')
@mock.patch.object(Client, 'captureException')
def test_mailer_failure_gets_sent_to_sentry(raven_client, mailer_exception):
    msg = ('Subject', 'Body', 'sender@example.com', ['receiver@example.com'])
    mail.send_mass_mail((msg,))

    mailer_message = Message.objects.first()

    log = MessageLog.objects.log(
        message=mailer_message,
        result_code=RESULT_FAILURE,
        log_message="Houston, we have a problem",
    )

    raven_client.assert_called_once_with(exc_info=mailer_exception(log.log_message))


@mock.patch.object(Client, 'captureException')
def test_mailer_success_not_sent_to_sentry(raven_client):
    msg = ('Subject', 'Body', 'sender@example.com', ['receiver@example.com'])
    mail.send_mass_mail((msg,))

    mailer_message = Message.objects.first()

    MessageLog.objects.log(
        message=mailer_message,
        result_code=RESULT_SUCCESS,
        log_message="Houston, life is good",
    )

    raven_client.assert_not_called()
