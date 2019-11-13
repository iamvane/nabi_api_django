# Generated by Django 2.2.6 on 2019-11-14 01:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0026_delete_address'),
    ]

    operations = [
        migrations.AlterField(
            model_name='instructorlessonrate',
            name='mins30',
            field=models.DecimalField(decimal_places=4, max_digits=9),
        ),
        migrations.AlterField(
            model_name='instructorlessonrate',
            name='mins45',
            field=models.DecimalField(decimal_places=4, max_digits=9),
        ),
        migrations.AlterField(
            model_name='instructorlessonrate',
            name='mins60',
            field=models.DecimalField(decimal_places=4, max_digits=9),
        ),
        migrations.AlterField(
            model_name='instructorlessonrate',
            name='mins90',
            field=models.DecimalField(decimal_places=4, max_digits=9),
        ),
    ]
