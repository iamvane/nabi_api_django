from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from accounts.models import get_account

User = get_user_model()


class Command(BaseCommand):
    """Set referral_token for all existing users, overwriting current data"""
    help = 'Set referral_token for all existing users'

    def handle(self, *args, **options):
        res = 'Z'
        while res not in ['Y', 'N']:
            res = input('Are you sure to overwrite existing referral_token values? (Y/N)')
            res = res.upper()
            if res not in ['Y', 'N']:
                self.stdout.write('Wrong option. Please respond with Y or N\n\n')
                self.stdout.flush()
        if res == 'N':
            self.stdout.write('Process aborted.')
            self.stdout.flush()
            exit()
        self.stdout.write('Start process ...')
        self.stdout.flush()
        for user in User.objects.order_by('id'):
            account = get_account(user)
            if not account:
                continue
            user.referral_token = ''
            user.save()
            account.set_referral_token()
        self.stdout.write('Process complete ...')
        self.stdout.flush()
