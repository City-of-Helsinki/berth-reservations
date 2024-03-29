# Generated by Django 3.1 on 2020-11-17 09:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0023_add_common_area_image_file"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="berthtype",
            name="price_group",
        ),
        migrations.AddField(
            model_name="pier",
            name="price_tier",
            field=models.PositiveSmallIntegerField(
                choices=[(1, "Tier 1"), (2, "Tier 2"), (3, "Tier 3")],
                default=1,
                verbose_name="price tier",
            ),
            preserve_default=False,
        ),
    ]
