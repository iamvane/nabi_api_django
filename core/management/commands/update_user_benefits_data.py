from django.core.management import BaseCommand

from core.constants import BENEFIT_AMOUNT, BENEFIT_DISCOUNT, BENEFIT_LESSON, BENEFIT_PENDING, BENEFIT_READY
from core.models import UserBenefits


class Command(BaseCommand):
    """Update data in UserBenefits model due to changes in it"""
    help = 'Update data in UserBenefits model due to changes in it'

    def handle(self, *args, **options):
        self.stdout.write('Start update process ...')
        self.stdout.flush()
        # Update registered benefits of referrer
        for user_benefit in UserBenefits.objects.filter(status='disable', benefit_type=BENEFIT_LESSON):
            user_benefit.status = BENEFIT_PENDING
            user_benefit.benefit_type = BENEFIT_AMOUNT
            user_benefit.benefit_qty = 5
            user_benefit.source = 'Registration of referred user'
            user_benefit.depends_on = UserBenefits.objects.filter(beneficiary_id=user_benefit.provider_id,
                                                                  provider_id=user_benefit.beneficiary_id,
                                                                  benefit_type=BENEFIT_LESSON,
                                                                  status='enable').last()
            user_benefit.save()
        # Update registered benefits of referred
        for user_benefit in UserBenefits.objects.filter(status='enable', benefit_type=BENEFIT_LESSON):
            user_benefit.status = BENEFIT_READY
            user_benefit.benefit_type = BENEFIT_DISCOUNT
            user_benefit.benefit_qty = 20
            user_benefit.source = 'User registration with referral token'
            user_benefit.save()
        self.stdout.write('Update process complete ...')
        self.stdout.flush()
