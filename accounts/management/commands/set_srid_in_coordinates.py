from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.core.management import BaseCommand

from accounts.models import get_account

User = get_user_model()


class Command(BaseCommand):
    """Set default value for srid param, in coordinates. This is a single-use command."""
    args = ''
    help = 'Set srid=4326 for every stored coordinates'

    def handle(self, *args, **options):
        self.stdout.write('Begin update process ...')
        self.stdout.flush()
        for user in User.objects.all():
            account = get_account(user)
            if account and account.coordinates:
                account.coordinates = Point(account.coordinates[0], account.coordinates[1], srid=4326)
                account.save()
        self.stdout.write('Update done successfully')
