# Generated by Django 2.2.6 on 2020-04-15 20:06

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('payments', '0003_auto_20200109_1544'),
    ]

    operations = [
        migrations.RenameField(
            model_name='payment',
            old_name='charge_id',
            new_name='operation_id',
        ),
        migrations.AlterField(
            model_name='payment',
            name='status',
            field=models.CharField(choices=[('registered', 'registered'), ('processed', 'processed'), ('applied', 'applied'), ('cancelled', 'cancelled')], default='registered', max_length=100),
        ),
        migrations.CreateModel(
            name='UserPaymentMethod',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stripe_payment_method_id', models.CharField(max_length=200)),
                ('is_main', models.BooleanField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_methods', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='payment',
            name='payment_method',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='charges', to='payments.UserPaymentMethod'),
        ),
    ]