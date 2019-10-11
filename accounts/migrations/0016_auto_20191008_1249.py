# Generated by Django 2.2.3 on 2019-10-08 16:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0015_auto_20191007_1818'),
    ]

    operations = [
        migrations.AlterField(
            model_name='education',
            name='degree_type',
            field=models.CharField(choices=[('associate', 'Associate Degree'), ('bachelors', "Bachelor's Degree"), ('graduate', 'Graduate Degreee'), ('professional', 'Professional Degree'), ('certification', 'Certification'), ('other', 'Other')], max_length=100),
        ),
        migrations.AlterField(
            model_name='education',
            name='field_of_study',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='education',
            name='graduation_year',
            field=models.IntegerField(),
        ),
        migrations.AlterField(
            model_name='education',
            name='school',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='education',
            name='school_location',
            field=models.CharField(max_length=100),
        ),
    ]