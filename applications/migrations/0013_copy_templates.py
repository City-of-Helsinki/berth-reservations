from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("django_ilmoitin", "0002_add_admin_notifications"),
        ("applications", "0012_berth_switch_reason"),
    ]

    # This migration was used to copy notifications templates from an inbuilt
    # "notifications" app to "django-ilmoitin". We are deleting the "notifications"
    # app altogether, so we have to remove any mention of it in this file.
    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop)
    ]
