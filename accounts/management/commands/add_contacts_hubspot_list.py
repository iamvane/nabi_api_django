from django.core.management import BaseCommand

from accounts.utils import add_to_email_list
from core.models import User


class Command(BaseCommand):
    help = 'Create account in HubSpot and add to a list'

    def handle(self, *args, **options):
        self.stdout.write('Start process ...')
        self.stdout.flush()
        for user in User.objects.all():
            # add account to list; in that function, the contact is created too
            if user.is_instructor():
                add_to_email_list(user, ['instructors'])
            if user.is_parent():
                add_to_email_list(user, ['parents'])
            if user.is_student():
                add_to_email_list(user, ['students'])
            self.stdout.write(' . ')
            self.stdout.flush()
        self.stdout.write('Process complete ...')
        self.stdout.flush()
