# Generated by Django 2.2.3 on 2019-09-16 15:23

from django.db import migrations
import uuid


def set_refer_token(apps, schema_editor):
    def set_token(model):
        for row in model.objects.all():
            row.referral_token = uuid.uuid4()
            row.save(update_fields=['referral_token'])

    Instructor = apps.get_model('accounts', 'Instructor')
    set_token(Instructor)
    Student = apps.get_model('accounts', 'Student')
    set_token(Student)
    Parent = apps.get_model('accounts', 'Parent')
    set_token(Parent)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_auto_20190916_1123'),
    ]

    operations = [
        migrations.RunPython(set_refer_token),
    ]
