# Generated by Django 2.2 on 2019-05-16 10:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("applications", "0010_set_defaults_for_required_fields")]

    operations = [
        migrations.AlterModelOptions(
            name="winterstoragereservation",
            options={
                "permissions": (
                    ("resend_reservation", "Can resend confirmation for applications"),
                )
            },
        ),
        migrations.AlterField(
            model_name="berthreservation",
            name="address",
            field=models.CharField(max_length=150, verbose_name="address"),
        ),
        migrations.AlterField(
            model_name="berthreservation",
            name="boat_length",
            field=models.DecimalField(
                decimal_places=2, max_digits=5, verbose_name="boat length"
            ),
        ),
        migrations.AlterField(
            model_name="berthreservation",
            name="boat_width",
            field=models.DecimalField(
                decimal_places=2, max_digits=5, verbose_name="boat width"
            ),
        ),
        migrations.AlterField(
            model_name="berthreservation",
            name="email",
            field=models.EmailField(max_length=254, verbose_name="email address"),
        ),
        migrations.AlterField(
            model_name="berthreservation",
            name="first_name",
            field=models.CharField(max_length=40, verbose_name="first name"),
        ),
        migrations.AlterField(
            model_name="berthreservation",
            name="last_name",
            field=models.CharField(max_length=150, verbose_name="last name"),
        ),
        migrations.AlterField(
            model_name="berthreservation",
            name="municipality",
            field=models.CharField(max_length=64, verbose_name="municipality"),
        ),
        migrations.AlterField(
            model_name="berthreservation",
            name="phone_number",
            field=models.CharField(max_length=64, verbose_name="phone number"),
        ),
        migrations.AlterField(
            model_name="berthreservation",
            name="zip_code",
            field=models.CharField(max_length=64, verbose_name="zip code"),
        ),
        migrations.AlterField(
            model_name="winterstoragereservation",
            name="address",
            field=models.CharField(max_length=150, verbose_name="address"),
        ),
        migrations.AlterField(
            model_name="winterstoragereservation",
            name="boat_length",
            field=models.DecimalField(
                decimal_places=2, max_digits=5, verbose_name="boat length"
            ),
        ),
        migrations.AlterField(
            model_name="winterstoragereservation",
            name="boat_width",
            field=models.DecimalField(
                decimal_places=2, max_digits=5, verbose_name="boat width"
            ),
        ),
        migrations.AlterField(
            model_name="winterstoragereservation",
            name="email",
            field=models.EmailField(max_length=254, verbose_name="email address"),
        ),
        migrations.AlterField(
            model_name="winterstoragereservation",
            name="first_name",
            field=models.CharField(max_length=40, verbose_name="first name"),
        ),
        migrations.AlterField(
            model_name="winterstoragereservation",
            name="last_name",
            field=models.CharField(max_length=150, verbose_name="last name"),
        ),
        migrations.AlterField(
            model_name="winterstoragereservation",
            name="municipality",
            field=models.CharField(max_length=64, verbose_name="municipality"),
        ),
        migrations.AlterField(
            model_name="winterstoragereservation",
            name="phone_number",
            field=models.CharField(max_length=64, verbose_name="phone number"),
        ),
        migrations.AlterField(
            model_name="winterstoragereservation",
            name="storage_method",
            field=models.CharField(
                choices=[
                    ("on_trestles", "On trestles"),
                    ("on_trailer", "On a trailer"),
                    ("under_tarp", "Under a tarp"),
                ],
                max_length=60,
                verbose_name="Storage method",
            ),
        ),
        migrations.AlterField(
            model_name="winterstoragereservation",
            name="zip_code",
            field=models.CharField(max_length=64, verbose_name="zip code"),
        ),
    ]
