# Generated by Django 2.1.7 on 2019-04-02 07:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("harbors", "0005_add_titles_for_avlblty_levels")]

    operations = [
        migrations.RemoveField(model_name="availabilitylevel", name="identifier"),
        migrations.RemoveField(model_name="boattype", name="identifier"),
        migrations.RemoveField(model_name="harbor", name="identifier"),
    ]
