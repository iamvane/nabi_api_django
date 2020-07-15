from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from accounts.models import get_account

User = get_user_model()


class Command(BaseCommand):
    """Set timezone value, from coordinates or location (zip code)"""
    args = ''
    help = 'Set timezone, from coordinates or location (zip code)'

    def handle(self, *args, **options):
        self.stdout.write('Start update process')
        self.stdout.flush()
        for user in User.objects.all():
            account = get_account(user)
            if account:
                time_zone = account.get_timezone_from_location_zipcode(default_value='')
                if time_zone:
                    account.timezone = time_zone
                    account.save()
        self.stdout.write('Update process was complete')
