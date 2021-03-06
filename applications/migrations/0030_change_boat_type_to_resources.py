# Generated by Django 3.1 on 2021-03-25 11:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0027_map_harbors_with_resources"),
        ("applications", "0029_replace_harborchoice_harbors_with_resources"),
    ]

    operations = [
        migrations.AlterField(
            model_name="berthapplication",
            name="boat_type",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="resources.boattype",
                verbose_name="boat type",
            ),
        ),
        migrations.AlterField(
            model_name="berthapplication",
            name="chosen_harbors",
            field=models.ManyToManyField(
                blank=True,
                through="applications.HarborChoice",
                to="resources.Harbor",
                verbose_name="chosen harbors",
            ),
        ),
        migrations.AlterField(
            model_name="winterstorageapplication",
            name="boat_type",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="resources.boattype",
                verbose_name="boat type",
            ),
        ),
    ]
