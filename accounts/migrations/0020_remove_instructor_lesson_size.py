# Generated by Django 2.2.6 on 2019-10-14 18:04

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0019_instructor_lesson_size'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='instructor',
            name='lesson_size',
        ),
    ]
