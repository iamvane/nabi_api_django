from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from accounts.models import get_account
from accounts.utils import get_geopoint_from_location

User = get_user_model()


class Command(BaseCommand):
    """Set coordinates from location, set timezone from coordinates or location (zip code)"""
    args = ''
    help = 'Set coordinates and timezone values'

    def handle(self, *args, **options):
        self.stdout.write('Start update process')
        self.stdout.flush()
        for user in User.objects.all():
            account = get_account(user)
            if account:
                if not account.location:
                    self.stdout.write(f'{user.email} has not location')
                    continue
                account.coordinates = get_geopoint_from_location(account.location)
                account.save()
                time_zone = account.get_timezone_from_location_zipcode(default_value='')
                if time_zone:
                    account.timezone = time_zone
                    account.save()
        self.stdout.write('Update process was complete')
