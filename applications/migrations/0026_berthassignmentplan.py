# Generated by Django 3.1 on 2020-10-08 21:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0020_change_berth_number_to_char'),
        ('applications', '0025_add_application_area_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='BerthAssignmentPlan',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('application', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='applications.berthapplication')),
                ('berth', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='resources.berth')),
            ],
        ),
    ]
