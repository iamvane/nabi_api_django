# Generated by Django 2.2.3 on 2019-09-11 16:19

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_merge_20190911_1005'),
    ]

    operations = [
        migrations.AlterField(
            model_name='instructor',
            name='music',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=100), blank=True, null=True, size=None),
        ),
    ]