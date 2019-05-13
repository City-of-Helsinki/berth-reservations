from django.db.models.signals import post_save
from django.dispatch import receiver
from mailer.models import MessageLog, RESULT_FAILURE
from sentry_sdk import capture_exception


class MailerFailureException(Exception):
    pass


@receiver(post_save, sender=MessageLog)
def mailer_message_failure_handler(sender, **kwargs):
    message_failure_log = kwargs.get("instance")
    created = kwargs.get("created")

    if created and message_failure_log.result == RESULT_FAILURE:
        capture_exception(MailerFailureException(message_failure_log.log_message))
