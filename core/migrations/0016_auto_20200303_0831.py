# Generated by Django 2.2.6 on 2020-03-03 13:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_auto_20200214_2109'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userbenefits',
            name='status',
            field=models.CharField(choices=[('ready', 'ready'), ('cancelled', 'cancelled'), ('pending', 'pending'), ('used', 'used')], max_length=50),
        ),
    ]