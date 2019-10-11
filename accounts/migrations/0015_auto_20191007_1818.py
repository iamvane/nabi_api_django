# Generated by Django 2.2.3 on 2019-10-07 22:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0014_auto_20191004_1651'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='availability',
            name='day_of_week',
        ),
        migrations.RemoveField(
            model_name='availability',
            name='from1',
        ),
        migrations.RemoveField(
            model_name='availability',
            name='to',
        ),
        migrations.AddField(
            model_name='availability',
            name='fri10to12',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='fri12to3',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='fri3to6',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='fri6to9',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='fri8to10',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='mon10to12',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='mon12to3',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='mon3to6',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='mon6to9',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='mon8to10',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='sat10to12',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='sat12to3',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='sat3to6',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='sat6to9',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='sat8to10',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='sun10to12',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='sun12to3',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='sun3to6',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='sun6to9',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='sun8to10',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='thu10to12',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='thu12to3',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='thu3to6',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='thu6to9',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='thu8to10',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='tue10to12',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='tue12to3',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='tue3to6',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='tue6to9',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='tue8to10',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='wed10to12',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='wed12to3',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='wed3to6',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='wed6to9',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='availability',
            name='wed8to10',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='instructorinstruments',
            name='skill_level',
            field=models.CharField(blank=True, choices=[('beginner', 'beginner'), ('intermediate', 'intermediate'), ('advanced', 'advanced')], max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='studentdetails',
            name='skill_level',
            field=models.CharField(choices=[('beginner', 'beginner'), ('intermediate', 'intermediate'), ('advanced', 'advanced')], max_length=50),
        ),
    ]