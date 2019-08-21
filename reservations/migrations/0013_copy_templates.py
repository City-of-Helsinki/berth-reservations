import django.contrib.gis.db.models.fields
from django.db import connection, migrations, models


def copy_templates_data(apps, schema_editor):
    NotificationTemplate = apps.get_model("django_ilmoitin", "NotificationTemplate")
    OldNotificationTemplate = apps.get_model("notifications", "NotificationTemplate")
    NotificationTemplateTranslation = apps.get_model(
        "django_ilmoitin", "NotificationTemplateTranslation"
    )
    OldNotificationTemplateTranslation = apps.get_model(
        "notifications", "NotificationTemplateTranslation"
    )

    NotificationTemplate.objects.bulk_create(OldNotificationTemplate.objects.all())

    for template in OldNotificationTemplate.objects.all():
        for admin in template.admins_to_notify.all():
            nt = NotificationTemplate.objects.get(pk=template.pk)
            nt.admins_to_notify.add(admin)

    for translation in OldNotificationTemplateTranslation.objects.all():
        NotificationTemplateTranslation.objects.create(
            master_id=translation.pk,
            language_code=translation.language_code,
            subject=translation.subject,
            body_html=translation.html_body,
            body_text=translation.text_body,
        )


def delete_templates_data(apps, schema_editor):
    NotificationTemplate = apps.get_model("django_ilmoitin", "NotificationTemplate")
    NotificationTemplate.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("django_ilmoitin", "0002_add_admin_notifications"),
        ("reservations", "0012_berth_switch_reason"),
    ]

    operations = [migrations.RunPython(copy_templates_data, delete_templates_data)]
