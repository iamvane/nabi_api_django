# Generated by Django 2.2.6 on 2019-12-16 23:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lesson', '0003_auto_20191009_1317'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lessonrequest',
            name='instrument',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='lesson.Instrument'),
        ),
        migrations.AlterField(
            model_name='lessonrequest',
            name='lessons_duration',
            field=models.CharField(choices=[('30 mins', '30 mins'), ('45 mins', '45 mins'), ('60 mins', '60 mins'), ('90 mins', '90 mins')], max_length=100),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='lessonrequest',
            name='place_for_lessons',
            field=models.CharField(choices=[('home', 'home'), ('studio', 'studio'), ('online', 'online')], max_length=100),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='lessonrequest',
            name='skill_level',
            field=models.CharField(choices=[('beginner', 'beginner'), ('intermediate', 'intermediate'), ('advanced', 'advanced')], max_length=100),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='lessonrequest',
            name='status',
            field=models.CharField(blank=True, choices=[('seen', 'seen'), ('no seen', 'no seen')], default='no seen', max_length=100),
        ),
    ]
