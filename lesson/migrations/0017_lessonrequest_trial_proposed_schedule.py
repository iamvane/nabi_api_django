# Generated by Django 2.2.6 on 2020-05-19 20:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lesson', '0016_auto_20200508_0919'),
    ]

    operations = [
        migrations.AddField(
            model_name='lessonrequest',
            name='trial_proposed_schedule',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]