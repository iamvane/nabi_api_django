from django.core.management import BaseCommand

from accounts.models import Instructor


class Command(BaseCommand):
    """Update complete field for all instructors"""
    args = ''
    help = 'Update complete field for all instructors'

    def handle(self, *args, **options):
        self.stdout.write('Start update process ...')
        self.stdout.flush()
        for instructor in Instructor.objects.all():
            instructor.update_complete()
        self.stdout.write('Update process completed ...')
        self.stdout.flush()
