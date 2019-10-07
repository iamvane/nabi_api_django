import secrets

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from .constants import (
    BENEFIT_DISABLED, BENEFIT_ENABLED, BENEFIT_LESSON, BENEFIT_STATUSES, BENEFIT_TYPES,
    ROLE_INSTRUCTOR, ROLE_PARENT, ROLE_STUDENT,
)


class UserManager(BaseUserManager):
    """Define required methods for custom User model usage."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Common operations when create an user."""
        if not email:
            raise ValueError('Email value is required.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
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


def generate_token():
    return secrets.token_urlsafe(12)


class User(AbstractUser):
    email = models.EmailField('email address', unique=True)
    username = models.CharField(blank=True, default='', max_length=120)
    referral_token = models.CharField(max_length=20, default=generate_token, blank=True, unique=True)
    referred_by = models.ForeignKey('self', blank=True, null=True, related_name='referrals', on_delete=models.SET_NULL)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def get_role(self):
        if hasattr(self, 'instructor'):
            return ROLE_INSTRUCTOR
        elif hasattr(self, 'parent'):
            return ROLE_PARENT
        else:
            return ROLE_STUDENT

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
            UserBenefits.objects.create(user=self, user_origin=self.referred_by,
                                        benefit_type=BENEFIT_LESSON, status=BENEFIT_ENABLED)
            # add benefit to referring user
            UserBenefits.objects.create(user=self.referred_by, user_origin=self,
                                        benefit_type=BENEFIT_LESSON, status=BENEFIT_DISABLED)


class UserToken(models.Model):
    """Model to store token used in reset password."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=40, unique=True)
    expired_at = models.DateTimeField()


class UserBenefits(models.Model):
    user = models.ForeignKey(User, related_name='benefits', on_delete=models.CASCADE)
    benefit_type = models.CharField(max_length=50, choices=BENEFIT_TYPES)
    user_origin = models.ForeignKey(User, related_name='provided_benefits', on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=50, choices=BENEFIT_STATUSES)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
