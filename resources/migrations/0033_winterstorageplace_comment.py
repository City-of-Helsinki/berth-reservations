# Generated by Django 3.2.12 on 2022-05-04 11:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0032_remove_unique_from_servicemap_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="winterstorageplace",
            name="comment",
            field=models.TextField(blank=True, verbose_name="comment"),
        ),
    ]
