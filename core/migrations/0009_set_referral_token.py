from django.db import migrations
import secrets


def set_refer_token(apps, schema_editor):
    def set_token(model):
        for row in model.objects.all():
            row.referral_token = secrets.token_urlsafe(12)
            row.save(update_fields=['referral_token'])

    User = apps.get_model('core', 'User')
    set_token(User)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_auto_20190920_1208'),
    ]

    operations = [
        migrations.RunPython(set_refer_token),
    ]
