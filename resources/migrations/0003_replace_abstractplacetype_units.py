# Generated by Django 2.2.6 on 2020-02-12 13:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0002_add_berth_comments"),
    ]

    operations = [
        migrations.AlterField(
            model_name="berthtype",
            name="length",
            field=models.DecimalField(
                decimal_places=2, max_digits=10, verbose_name="length (m)"
            ),
        ),
        migrations.RunSQL(
            sql="UPDATE resources_berthtype SET length = length/100;",
            reverse_sql="UPDATE resources_berthtype SET length = length*100;",
        ),
        migrations.AlterField(
            model_name="berthtype",
            name="length",
            field=models.DecimalField(
                decimal_places=2, max_digits=5, verbose_name="length (m)"
            ),
        ),
        migrations.AlterField(
            model_name="berthtype",
            name="width",
            field=models.DecimalField(
                decimal_places=2, max_digits=10, verbose_name="width (m)"
            ),
        ),
        migrations.RunSQL(
            sql="UPDATE resources_berthtype SET width = width/100;",
            reverse_sql="UPDATE resources_berthtype SET width = width*100;",
        ),
        migrations.AlterField(
            model_name="berthtype",
            name="width",
            field=models.DecimalField(
                decimal_places=2, max_digits=5, verbose_name="width (m)"
            ),
        ),
        migrations.AlterField(
            model_name="winterstorageplacetype",
            name="length",
            field=models.DecimalField(
                decimal_places=2, max_digits=10, verbose_name="length (m)"
            ),
        ),
        migrations.RunSQL(
            sql="UPDATE resources_winterstorageplacetype SET length = length/100;",
            reverse_sql="UPDATE resources_winterstorageplacetype SET length = length*100;",
        ),
        migrations.AlterField(
            model_name="winterstorageplacetype",
            name="length",
            field=models.DecimalField(
                decimal_places=2, max_digits=5, verbose_name="length (m)"
            ),
        ),
        migrations.AlterField(
            model_name="winterstorageplacetype",
            name="width",
            field=models.DecimalField(
                decimal_places=2, max_digits=10, verbose_name="width (m)"
            ),
        ),
        migrations.RunSQL(
            sql="UPDATE resources_winterstorageplacetype SET width = width/100;",
            reverse_sql="UPDATE resources_winterstorageplacetype SET width = width*100;",
        ),
        migrations.AlterField(
            model_name="winterstorageplacetype",
            name="width",
            field=models.DecimalField(
                decimal_places=2, max_digits=5, verbose_name="width (m)"
            ),
        ),
    ]
