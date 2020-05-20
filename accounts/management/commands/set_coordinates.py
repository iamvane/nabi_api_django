import re

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.core.management import BaseCommand

from accounts.models import get_account

User = get_user_model()


class Command(BaseCommand):
    """Set coordinates value, from latitude and longitude values"""
    args = ''
    help = 'Set coordinates with provided lat and long values'

    def handle(self, *args, **options):
        # first, ask for user identifier, and get it
        while True:
            identifier = input('Please indicate id or email of user to handle')
            if identifier.isnumeric() or re.match(r'.{2,}@.{2,}\..{2,}', identifier):
                break
            else:
                self.stdout.write('Wrong value. Please, provide id or email of user.\n')
                self.stdout.flush()
        if identifier.isnumeric():
            try:
                user = User.objects.get(id=identifier)
            except User.DoesNotExist:
                self.stdout.write('No User with provided id')
                exit()
        else:
            try:
                user = User.objects.get(email=identifier)
            except User.DoesNotExist:
                self.stdout.write('No User with provided email')
                exit()
        # second, ask for coordinates
        latitude = None
        while latitude is None:
            try:
                latitude = float(input('Please, provide latitude: '))
            except ValueError:
                self.stdout.write('Please, provide a valid float number\n')
        longitude = None
        while longitude is None:
            try:
                longitude = float(input('Please, provide longitude: '))
            except ValueError:
                self.stdout.write('Please, provide a valid float number\n')

        account = get_account(user)
        account.coordinates = Point(longitude, latitude, srid=4326)
        account.save()
        self.stdout.write('Coordinates were stored successfully')
