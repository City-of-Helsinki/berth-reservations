# Generated by Django 2.1.2 on 2019-01-18 12:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("applications", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="HarborChoice",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("priority", models.PositiveSmallIntegerField(verbose_name="priority")),
                (
                    "harbor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="resources.Harbor",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="reservation",
            name="accept_boating_newsletter",
            field=models.BooleanField(
                default=False, verbose_name="accept boating newsletter"
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="accept_fitness_news",
            field=models.BooleanField(
                default=False, verbose_name="accept fitness news"
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="accept_library_news",
            field=models.BooleanField(
                default=False, verbose_name="accept library news"
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="accept_other_culture_news",
            field=models.BooleanField(
                default=False, verbose_name="accept other culture news"
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="accessibility_required",
            field=models.BooleanField(
                default=False, verbose_name="accessibility required"
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="address",
            field=models.CharField(blank=True, max_length=150, verbose_name="address"),
        ),
        migrations.AddField(
            model_name="reservation",
            name="agree_to_terms",
            field=models.BooleanField(
                blank=True, null=True, verbose_name="agree to terms"
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="boat_draught",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=5,
                null=True,
                verbose_name="boat draught",
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="boat_hull_material",
            field=models.CharField(
                blank=True, max_length=64, verbose_name="boat hull material"
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="boat_intended_use",
            field=models.CharField(
                blank=True, max_length=150, verbose_name="boat intended use"
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="boat_is_inspected",
            field=models.BooleanField(
                blank=True, null=True, verbose_name="boat is inspected"
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="boat_is_insured",
            field=models.BooleanField(
                blank=True, null=True, verbose_name="boat is insured"
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="boat_length",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=5,
                null=True,
                verbose_name="boat length",
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="boat_model",
            field=models.CharField(
                blank=True, max_length=64, verbose_name="boat model"
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="boat_name",
            field=models.CharField(blank=True, max_length=64, verbose_name="boat name"),
        ),
        migrations.AddField(
            model_name="reservation",
            name="boat_propulsion",
            field=models.CharField(
                blank=True, max_length=64, verbose_name="boat propulsion"
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="boat_registration_number",
            field=models.CharField(
                blank=True, max_length=64, verbose_name="boat registration number"
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="boat_type",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="applications",
                to="resources.BoatType",
                verbose_name="boat type",
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="boat_weight",
            field=models.PositiveIntegerField(
                blank=True, null=True, verbose_name="boat weight"
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="boat_width",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=5,
                null=True,
                verbose_name="boat width",
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="business_id",
            field=models.CharField(
                blank=True, max_length=64, verbose_name="business ID"
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="company_name",
            field=models.CharField(
                blank=True, max_length=150, verbose_name="company name"
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="information_accuracy_confirmed",
            field=models.BooleanField(
                default=False, verbose_name="information accuracy confirmed"
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="is_processed",
            field=models.BooleanField(default=False, verbose_name="is processed"),
        ),
        migrations.AddField(
            model_name="reservation",
            name="language",
            field=models.CharField(
                choices=[("fi", "Finnish"), ("en", "English"), ("sv", "Swedish")],
                default="fi",
                max_length=10,
                verbose_name="language",
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="municipality",
            field=models.CharField(
                blank=True, max_length=64, verbose_name="municipality"
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="phone_number",
            field=models.CharField(
                blank=True, max_length=64, verbose_name="phone number"
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="rent_from",
            field=models.CharField(blank=True, max_length=64, verbose_name="rent from"),
        ),
        migrations.AddField(
            model_name="reservation",
            name="rent_till",
            field=models.CharField(blank=True, max_length=64, verbose_name="rent till"),
        ),
        migrations.AddField(
            model_name="reservation",
            name="renting_period",
            field=models.CharField(
                blank=True, max_length=64, verbose_name="renting period"
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="zip_code",
            field=models.CharField(blank=True, max_length=64, verbose_name="zip code"),
        ),
        migrations.AddField(
            model_name="harborchoice",
            name="reservation",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="applications.Reservation",
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="chosen_harbors",
            field=models.ManyToManyField(
                blank=True,
                through="applications.HarborChoice",
                to="resources.Harbor",
                verbose_name="chosen harbors",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="harborchoice", unique_together={("reservation", "priority")}
        ),
    ]
