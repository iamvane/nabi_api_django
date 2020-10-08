# Generated by Django 2.2.6 on 2020-10-03 23:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lesson', '0027_auto_20200910_0825'),
    ]

    operations = [
        migrations.AddField(
            model_name='lessonrequest',
            name='gender',
            field=models.CharField(blank=True, choices=[('female', 'female'), ('male', 'male'), ('undisclosed', 'undisclosed')], max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='lessonrequest',
            name='language',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]