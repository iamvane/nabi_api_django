# Generated by Django 2.2.6 on 2020-01-09 20:44

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0002_auto_20200101_1833'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='payment',
            name='service',
        ),
        migrations.RemoveField(
            model_name='payment',
            name='service_id',
        ),
    ]