# Generated by Django 2.2.6 on 2020-01-17 16:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0033_auto_20200114_1052'),
    ]

    operations = [
        migrations.AddField(
            model_name='instructor',
            name='reference',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='instructor',
            name='terms_accepted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='parent',
            name='reference',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='parent',
            name='terms_accepted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='student',
            name='reference',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='student',
            name='terms_accepted',
            field=models.BooleanField(default=False),
        ),
    ]
