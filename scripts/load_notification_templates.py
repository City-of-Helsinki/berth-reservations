import logging
import os
import sys
from os import environ as env

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.setLevel(logging.DEBUG)
# create console handler and set level to debug
handler.setLevel(logging.DEBUG)

# add ch to logger
logger.addHandler(handler)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)


if "DJANGO_SETTINGS_MODULE" not in env:
    from berth_reservations import settings

    env.setdefault("DJANGO_SETTINGS_MODULE", settings.__name__)

if __name__ == "__main__":
    # Setup django
    import django

    django.setup()

    from django.conf import settings

    languages = settings.LANGUAGES

    # The rest of the imports that depend on Django
    from django.utils.translation import override
    from django_ilmoitin.models import NotificationTemplate
    from parler.utils.context import switch_language

    from applications.notifications import (
        NotificationType as ApplicationNotificationType,
    )
    from leases.notifications import NotificationType as LeaseNotificationType
    from payments.notifications import NotificationType as PaymentNotificationType

    notifications = {
        ApplicationNotificationType.BERTH_APPLICATION_CREATED: {
            "html": "berth_application_confirmation_{lang}.html",
            "plain": None,
        },
        ApplicationNotificationType.BERTH_APPLICATION_REJECTED: {
            "html": "berth_none_offered_{lang}.html",
            "plain": None,
        },
        ApplicationNotificationType.WINTER_STORAGE_APPLICATION_CREATED: {
            "html": "ws_application_confirmation_{lang}.html",
            "plain": None,
        },
        ApplicationNotificationType.UNMARKED_WINTER_STORAGE_APPLICATION_CREATED: {
            "html": "ws_application_confirmation_{lang}.html",
            "plain": None,
        },
        PaymentNotificationType.NEW_BERTH_ORDER_APPROVED: {
            "html": "berth_offer_new_{lang}.html",
            "plain": None,
        },
        PaymentNotificationType.RENEW_BERTH_ORDER_APPROVED: {
            "html": "berth_invoice_{lang}.html",
            "plain": "berth_invoice_{lang}.txt",
        },
        PaymentNotificationType.BERTH_SWITCH_ORDER_APPROVED: {
            "html": "berth_offer_switch_{lang}.html",
            "plain": None,
        },
        PaymentNotificationType.NEW_WINTER_STORAGE_ORDER_APPROVED: {
            "html": "ws_invoice_{lang}.html",
            "plain": None,
        },
        PaymentNotificationType.UNMARKED_WINTER_STORAGE_ORDER_APPROVED: {
            "html": "um_ws_invoice_{lang}.html",
            "plain": None,
        },
        PaymentNotificationType.ADDITIONAL_PRODUCT_ORDER_APPROVED: {
            "html": "additional_service_invoice_{lang}.html",
            "plain": None,
        },
        PaymentNotificationType.ORDER_CANCELLED: {
            "html": "order_cancelled_{lang}.html",
            "plain": None,
        },
        LeaseNotificationType.AUTOMATIC_INVOICING_EMAIL_ADMINS: {
            "html": "automatic_invoicing_email_admins_{lang}.html",
            "plain": "automatic_invoicing_email_admins_{lang}.txt",
        },
    }

    from scripts.generate_email_templates import generate_templates

    generate_templates()
    delete_result = NotificationTemplate.objects.all().delete()
    logger.info(f"Deleted: {delete_result}")

    for notification_index, (notification_type, templates) in enumerate(
        notifications.items()
    ):
        template = NotificationTemplate.objects.create(
            id=notification_index, type=notification_type.value,
        )
        for (lang, _name) in languages:
            full_html_path = None
            full_plain_path = None

            with override(lang), switch_language(template, lang):
                template.subject = notification_type.label

                if html_path := templates.get("html"):
                    full_html_path = os.path.join(
                        PROJECT_ROOT, "templates", "email", "generated", html_path
                    ).format(lang=lang)
                    # Check that the path for the specified language exists
                    if os.path.isfile(full_html_path):
                        with open(full_html_path, "r") as html_template_file:
                            template.body_html = str(html_template_file.read())

                if plain_path := templates.get("plain"):
                    full_plain_path = os.path.join(
                        PROJECT_ROOT, "templates", "email", "plain_messages", plain_path
                    ).format(lang=lang)
                    # Check that the path for the specified language exists
                    if os.path.isfile(full_plain_path):
                        with open(full_plain_path, "r") as plain_template_file:
                            template.body_text = str(plain_template_file.read())

                template.save()

        logger.info(f"Written template: {template}")
