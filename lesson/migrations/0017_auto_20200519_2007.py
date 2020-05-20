# Generated by Django 2.2.6 on 2020-05-20 03:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lesson', '0016_auto_20200508_0919'),
    ]

    operations = [
        migrations.AddField(
            model_name='lesson',
            name='scheduled_timezone',
            field=models.CharField(blank=True, max_length=6),
        ),
        migrations.AddField(
            model_name='lessonrequest',
            name='trial_proposed_datetime',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='lessonrequest',
            name='trial_proposed_timezone',
            field=models.CharField(blank=True, max_length=6),
        ),
    ]
