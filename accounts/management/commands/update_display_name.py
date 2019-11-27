from django.core.management import BaseCommand

from accounts.models import get_account
from core.models import User


class Command(BaseCommand):
    """Update display_name field with current values of first_name and last_name"""
    args = ''
    help = 'Update display_name field with values of first_name and last_name'

    def handle(self, *args, **options):
        self.stdout.write('Start update process ...')
        self.stdout.flush()
        for user in User.objects.all():
            account = get_account(user)
            if account is not None:
                account.set_display_name()
        self.stdout.write('Update process completed ...')
        self.stdout.flush()
