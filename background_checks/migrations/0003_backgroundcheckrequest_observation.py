# Generated by Django 2.2.6 on 2020-01-03 18:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('background_checks', '0002_auto_20200102_1102'),
    ]

    operations = [
        migrations.AddField(
            model_name='backgroundcheckrequest',
            name='observation',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
    ]
