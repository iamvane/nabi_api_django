# Generated by Django 2.2.6 on 2020-04-15 23:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0038_remove_instructor_qualifications'),
    ]

    operations = [
        migrations.AddField(
            model_name='instructor',
            name='stripe_customer_id',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='parent',
            name='stripe_customer_id',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='student',
            name='stripe_customer_id',
            field=models.CharField(blank=True, max_length=200),
        ),
    ]
