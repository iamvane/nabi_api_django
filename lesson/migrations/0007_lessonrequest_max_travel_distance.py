# Generated by Django 2.2.6 on 2019-12-19 15:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lesson', '0006_auto_20191217_1908'),
    ]

    operations = [
        migrations.AddField(
            model_name='lessonrequest',
            name='max_travel_distance',
            field=models.IntegerField(default=500),
            preserve_default=False,
        ),
    ]
