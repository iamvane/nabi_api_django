# Generated by Django 2.2.6 on 2020-08-10 20:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0047_instructorreview'),
    ]

    operations = [
        migrations.RenameField(
            model_name='instructorreview',
            old_name='rate',
            new_name='rating',
        ),
    ]
