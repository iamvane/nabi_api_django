from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils import timezone

from .constants import (
    BENEFIT_CANCELLED, BENEFIT_READY, BENEFIT_PENDING, BENEFIT_AMOUNT, BENEFIT_DISCOUNT, BENEFIT_LESSON,
    BENEFIT_STATUSES, BENEFIT_USED, BENEFIT_TYPES,
    ROLE_AFFILIATE, ROLE_INSTRUCTOR, ROLE_PARENT, ROLE_STUDENT,
)


class UserManager(BaseUserManager):
    """Define required methods for custom User model usage."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Common operations when create an user."""
        if not email:
            raise ValueError('Email value is required.')
        email = self.normalize_email(email)
        ind_at_sign = email.find('@')
        if ind_at_sign > 8:
            ind_at_sign = 8
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.referral_token = email[:ind_at_sign] + timezone.now().strftime('%H%M%S%f')
        user.save()
        user.set_user_benefits()
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    email = models.EmailField('email address', unique=True)
    username = models.CharField(blank=True, default='', max_length=120)
    referral_token = models.CharField(max_length=20, blank=True, unique=True)
    referred_by = models.ForeignKey('self', blank=True, null=True, related_name='referrals', on_delete=models.SET_NULL)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def get_role(self):
        if hasattr(self, 'instructor'):
            return ROLE_INSTRUCTOR
        elif hasattr(self, 'parent'):
            return ROLE_PARENT
        elif hasattr(self, 'student'):
            return ROLE_STUDENT
        elif hasattr(self, 'affiliate'):
            return ROLE_AFFILIATE
        else:
            return 'unknown'

    @classmethod
    def get_user_from_refer_code(cls, ref_code):
        """Get an user from his refer_code"""
        user = None
        try:
            user = cls.objects.get(referral_token=ref_code)
        except models.ObjectDoesNotExist:
            pass
        return user

    def set_user_benefits(self):
        """Create benefits to user whether have been referred by another user."""
        if self.referred_by:
            # add benefit to this user
            user_benefit = UserBenefits.objects.create(beneficiary=self, provider=self.referred_by,
                                                       benefit_type=BENEFIT_DISCOUNT, benefit_qty=20,
                                                       status=BENEFIT_READY,
                                                       source='User registration with referral token')
            # add benefit to referring user
            UserBenefits.objects.create(beneficiary=self.referred_by, provider=self, depends_on=user_benefit,
                                        benefit_type=BENEFIT_AMOUNT, benefit_qty=5,
                                        status=BENEFIT_PENDING, source='Registration of referred user')

    def is_instructor(self):
        return hasattr(self, 'instructor')

    def is_parent(self):
        return hasattr(self, 'parent')

    def is_student(self):
        return hasattr(self, 'student')


class UserToken(models.Model):
    """Model to store token used in reset password."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=40, unique=True)
    expired_at = models.DateTimeField()


class UserBenefits(models.Model):
    beneficiary = models.ForeignKey(User, related_name='benefits', on_delete=models.CASCADE)
    provider = models.ForeignKey(User, related_name='provided_benefits', on_delete=models.SET_NULL,
                                 blank=True, null=True)
    benefit_qty = models.DecimalField(max_digits=9, decimal_places=4)
    benefit_type = models.CharField(max_length=50, choices=BENEFIT_TYPES)
    source = models.CharField(max_length=300, blank=True)   # method/process used to obtain the benefit
    depends_on = models.ForeignKey('UserBenefits', on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name='dependants')
    status = models.CharField(max_length=50, choices=BENEFIT_STATUSES)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    @staticmethod
    def update_applicable_benefits(user):
        from lesson.utils import get_benefit_to_redeem
        # get info about applicable benefits
        benefit_data = get_benefit_to_redeem(user)
        user_benefit_ids = []
        # Update data for used benefit
        if benefit_data.get('free_lesson'):
            if benefit_data.get('source') == 'benefit':
                user_benefit = user.benefits.filter(status=BENEFIT_READY, benefit_type=BENEFIT_LESSON).first()
                user_benefit.benefit_qty -= 1
                if user_benefit.benefit_qty == 0:
                    user_benefit.status = BENEFIT_USED
                    user_benefit_ids.append(user_benefit.id)
                user_benefit.save()
        else:
            if benefit_data.get('amount'):   # It's assumed that amount discount is benefit only, not offer
                user_benefit = user.benefits.filter(status=BENEFIT_READY, benefit_type=BENEFIT_AMOUNT).first()
                user_benefit.status = BENEFIT_USED
                user_benefit.save()
                user_benefit_ids.append(user_benefit.id)
            if benefit_data.get('discount') and benefit_data.get('source') == 'benefit':
                user_benefit = user.benefits.filter(status=BENEFIT_READY, benefit_type=BENEFIT_DISCOUNT).first()
                user_benefit.status = BENEFIT_USED
                user_benefit.save()
                user_benefit_ids.append(user_benefit.id)
        # cancel discount benefit from registration, if was not used
        first_book_benefit = user.benefits.filter(status=BENEFIT_READY, benefit_type=BENEFIT_DISCOUNT,
                                                  source='User registration with referral token'
                                                  ).first()
        if first_book_benefit:
            first_book_benefit.status = BENEFIT_CANCELLED
            first_book_benefit.save()
            user_benefit_ids.append(first_book_benefit.id)
        # enable user's benefits that depends on usage of others benefits
        if user_benefit_ids:
            user.provided_benefits.filter(depends_on__in=user_benefit_ids, status=BENEFIT_PENDING)\
                .update(status=BENEFIT_READY)


class ProviderRequest(models.Model):
    """Model to register a request to provider"""
    METHOD_TYPES = (('GET', 'GET'),
                    ('POST', 'POST'),
                    ('PUT', 'PUT'),
                    ('PATCH', 'PATCH'),
                    ('DELETE', 'DELETE'),
                    )
    provider = models.CharField(max_length=50)
    api_name = models.CharField(max_length=200)
    url_request = models.CharField(max_length=500)
    method = models.CharField(max_length=50, choices=METHOD_TYPES)
    headers = JSONField(blank=True, default=dict)
    parameters = JSONField(blank=True, default=dict)
    data = JSONField(blank=True, default=dict)
    data_text = models.TextField(blank=True, default='')   # when json format is not accepted
    response_status = models.SmallIntegerField(blank=True, null=True)
    response_content = JSONField(blank=True, default=dict)
    response_content_text = models.TextField(blank=True, default='')   # when json format is not accepted
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class TaskLog(models.Model):
    """Register called asynchronous tasks, which will be deleted when processing"""
    task_name = models.CharField(max_length=200)
    args = JSONField()
    registered_at = models.DateTimeField(auto_now_add=True)


class ScheduledTask(models.Model):
    """To store info about a task to execute at specific datetime"""
    function_name = models.CharField(max_length=150)
    schedule = models.DateTimeField()
    executed = models.BooleanField(blank=True, default=False)
    parameters = JSONField(blank=True, default=dict)
