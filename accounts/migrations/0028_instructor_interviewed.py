# Generated by Django 2.2.6 on 2019-11-16 20:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0027_auto_20191113_2029'),
    ]

    operations = [
        migrations.AddField(
            model_name='instructor',
            name='interviewed',
            field=models.BooleanField(blank=True, default=False),
        ),
    ]
