# Generated by Django 2.2.3 on 2019-08-21 04:19

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Instrument',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=250)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='LessonRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('message', models.TextField()),
                ('skill_level', models.CharField(blank=True, choices=[('basic', 'basic'), ('advanced', 'advanced')], max_length=100, null=True)),
                ('place_for_lessons', models.CharField(blank=True, choices=[('home', 'home'), ('studio', 'studio'), ('online', 'online')], max_length=100, null=True)),
                ('lessons_duration', models.CharField(blank=True, choices=[('thirty', 'thirty'), ('forty five', 'forty five'), ('sixty', 'sixty'), ('ninety', 'ninety')], max_length=100, null=True)),
                ('status', models.CharField(blank=True, max_length=100, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('instrument', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='lesson.Instrument')),
            ],
        ),
        migrations.CreateModel(
            name='LessonStudent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('lesson', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='lesson.LessonRequest')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.Student')),
            ],
        ),
        migrations.AddField(
            model_name='lessonrequest',
            name='students',
            field=models.ManyToManyField(through='lesson.LessonStudent', to='accounts.Student'),
        ),
        migrations.AddField(
            model_name='lessonrequest',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
