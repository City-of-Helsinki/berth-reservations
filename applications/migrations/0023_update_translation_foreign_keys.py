# Generated by Django 3.0.8 on 2020-07-29 13:18

from django.db import migrations
import django.db.models.deletion
import parler.fields


class Migration(migrations.Migration):

    dependencies = [
        ("applications", "0022_update_ordering"),
    ]

    operations = [
        migrations.AlterField(
            model_name="berthswitchreasontranslation",
            name="master",
            field=parler.fields.TranslationsForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="translations",
                to="applications.BerthSwitchReason",
            ),
        ),
    ]