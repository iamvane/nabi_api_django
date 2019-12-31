from django.contrib.gis.geos import Point
from django.core.management import BaseCommand

from accounts.models import get_account
from core.models import User


class Command(BaseCommand):
    """Review stored coordinates and fix how them were stored"""
    args = ''
    help = 'Review stored coordinates and fix how them were stored'

    def handle(self, *args, **options):
        total_changes = 0
        self.stdout.write('Start reviewing process ...')
        self.stdout.flush()
        for user in User.objects.all():
            account = get_account(user)
            if not account or not account.coordinates:   # if has not required values, skip
                continue
            coord1 = account.coordinates[0]   # should be lng (negative value for USA)
            coord2 = account.coordinates[1]   # should be lat (positive value for USA)
            if coord1 > 0 and coord2 < 0:   # coordinates stored in inverse place
                self.stdout.write('Interchange coordinates places to user {}\n'.format(user.id))
                self.stdout.flush()
                point = Point(coord2, coord1)
                account.coordinates = point
                account.save()
                total_changes += 1
        self.stdout.write('\n** Total changes made: {}\n\n'.format(total_changes))
        self.stdout.write('Reviewed process complete ...')
        self.stdout.flush()
