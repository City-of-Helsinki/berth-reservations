# Generated by Django 2.2 on 2019-05-20 08:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("harbors", "0009_ensure_non_null_fields")]

    operations = [
        migrations.AlterField(
            model_name="harbor",
            name="email",
            field=models.EmailField(blank=True, max_length=100, verbose_name="Email"),
        ),
        migrations.AlterField(
            model_name="harbor",
            name="image_link",
            field=models.URLField(
                blank=True, max_length=400, verbose_name="Image link"
            ),
        ),
        migrations.AlterField(
            model_name="harbor",
            name="phone",
            field=models.CharField(
                blank=True, max_length=30, verbose_name="Phone number"
            ),
        ),
        migrations.AlterField(
            model_name="harbor",
            name="www_url",
            field=models.URLField(blank=True, max_length=400, verbose_name="WWW link"),
        ),
        migrations.AlterField(
            model_name="harbor",
            name="zip_code",
            field=models.CharField(max_length=10, verbose_name="Postal code"),
        ),
        migrations.AlterField(
            model_name="winterstoragearea",
            name="email",
            field=models.EmailField(blank=True, max_length=100, verbose_name="Email"),
        ),
        migrations.AlterField(
            model_name="winterstoragearea",
            name="image_link",
            field=models.URLField(
                blank=True, max_length=400, verbose_name="Image link"
            ),
        ),
        migrations.AlterField(
            model_name="winterstoragearea",
            name="phone",
            field=models.CharField(
                blank=True, max_length=30, verbose_name="Phone number"
            ),
        ),
        migrations.AlterField(
            model_name="winterstoragearea",
            name="www_url",
            field=models.URLField(blank=True, max_length=400, verbose_name="WWW link"),
        ),
        migrations.AlterField(
            model_name="winterstoragearea",
            name="zip_code",
            field=models.CharField(max_length=10, verbose_name="Postal code"),
        ),
    ]