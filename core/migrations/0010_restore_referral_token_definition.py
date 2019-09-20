import core.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_set_referral_token'),
    ]

    operations = [
        migrations.AlterField(
            model_name='User',
            name='referral_token',
            field=models.CharField(blank=True, default=core.models.generate_token, max_length=20, unique=True),
        ),
    ]
