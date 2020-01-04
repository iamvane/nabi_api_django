# Generated by Django 2.2.6 on 2019-11-08 21:23

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_userbenefits'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProviderRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider', models.CharField(max_length=50)),
                ('api_name', models.CharField(max_length=200)),
                ('url_request', models.CharField(max_length=500)),
                ('method', models.CharField(choices=[('GET', 'GET'), ('POST', 'POST'), ('PUT', 'PUT'), ('PATCH', 'PATCH'), ('DELETE', 'DELETE')], max_length=50)),
                ('headers', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict)),
                ('parameters', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict)),
                ('data', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict)),
                ('data_text', models.TextField(blank=True, default='')),
                ('response_status', models.SmallIntegerField(blank=True, null=True)),
                ('response_content', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict)),
                ('response_content_text', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]