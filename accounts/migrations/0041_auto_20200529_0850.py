# Generated by Django 2.2.6 on 2020-05-29 15:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0040_auto_20200523_1303'),
    ]

    operations = [
        migrations.AlterField(
            model_name='instructor',
            name='video',
            field=models.URLField(blank=True, default='', verbose_name='URL of video file'),
        ),
    ]
