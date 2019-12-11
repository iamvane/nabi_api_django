from django.contrib.gis.geos import Point
from django.core.management import BaseCommand

from accounts.models import get_account
from core.models import User


class Command(BaseCommand):
    """Copy lat and lng data to coordinates field"""
    args = ''
    help = 'Copy lat and lng data to coordinates field'

    def handle(self, *args, **options):
        self.stdout.write('Start copy process ...')
        self.stdout.flush()
        for user in User.objects.all():
            account = get_account(user)
            if not account or account.coordinates:   # if has coordinates value already, skip
                continue
            if account.lat is not None and account.lng is not None and account.lat != '' and account.lng != '':
                account.coordinates = Point(float(account.lat), float(account.lng))
                account.save()
        self.stdout.write('Copy process complete ...')
        self.stdout.flush()
