import django.contrib.gis.db.models.fields
from django.db import connection, migrations, models


def copy_templates_data(apps, schema_editor):
    NotificationTemplate = apps.get_model("django_ilmoitin", "NotificationTemplate")
    NotificationTemplate.__bases__ = (models.Model,)
    OldNotificationTemplate = apps.get_model("notifications", "NotificationTemplate")
    NotificationTemplateTranslation = apps.get_model(
        "django_ilmoitin", "NotificationTemplateTranslation"
    )
    OldNotificationTemplateTranslation = apps.get_model(
        "notifications", "NotificationTemplateTranslation"
    )

    for template in OldNotificationTemplate.objects.all():
        nt = NotificationTemplate.objects.create(
            type=template.type,
            from_email=template.from_email,
            admin_notification_subject=template.admin_notification_subject,
            admin_notification_text=template.admin_notification_text,
        )
        for translation in OldNotificationTemplateTranslation.objects.filter(
            master_id=template.pk
        ):
            NotificationTemplateTranslation.objects.create(
                master_id=nt.pk,
                language_code=translation.language_code,
                subject=translation.subject,
                body_html=translation.html_body,
                body_text=translation.text_body,
            )
        for admin in template.admins_to_notify.all():
            nt.admins_to_notify.add(admin)


def delete_templates_data(apps, schema_editor):
    NotificationTemplate = apps.get_model("django_ilmoitin", "NotificationTemplate")
    NotificationTemplate.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("django_ilmoitin", "0002_add_admin_notifications"),
        ("reservations", "0012_berth_switch_reason"),
    ]

    operations = [migrations.RunPython(copy_templates_data, delete_templates_data)]
