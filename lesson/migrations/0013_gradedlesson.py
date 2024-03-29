# Generated by Django 2.2.6 on 2020-02-04 14:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lesson', '0012_lessonbooking_description'),
    ]

    operations = [
        migrations.CreateModel(
            name='GradedLesson',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('grade', models.PositiveSmallIntegerField()),
                ('lesson_date', models.DateField()),
                ('comment', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='graded_lessons', to='lesson.LessonBooking')),
            ],
        ),
    ]
