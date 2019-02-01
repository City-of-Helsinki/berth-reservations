from django.db.models.signals import post_save
from django.dispatch import receiver
from mailer.models import MessageLog, RESULT_FAILURE
from raven import Client


class MailerFailureException(Exception):
    pass


@receiver(post_save, sender=MessageLog)
def mailer_message_failure_handler(sender, **kwargs):
    message_failure_log = kwargs.get('instance')
    created = kwargs.get('created')

    if created and message_failure_log.result == RESULT_FAILURE:
        raven_client = Client()
        raven_client.captureException(
            exc_info=MailerFailureException(message_failure_log.log_message)
        )
