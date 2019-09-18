from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from accounts.models import Instructor, InstructorBenefits, Parent, ParentBenefits, Student, StudentBenefits
from core.constants import BENEFIT_LESSON, BENEFIT_ENABLED, BENEFIT_DISABLED, ROLE_INSTRUCTOR, ROLE_PARENT, ROLE_STUDENT


User = get_user_model()


@receiver(pre_save, sender=User)
def set_username(sender, instance, **kwargs):
    if instance.username != instance.email:
        instance.username = instance.email


def set_benefit_to_referrer(target_user, origin_user, benefit_type, benefit_status):
    """account can be Instructor, Parent or Student."""
    role = target_user.get_role()
    if role == ROLE_INSTRUCTOR:
        InstructorBenefits.objects.create(instructor=target_user.instructor, user_origin=origin_user,
                                          benefit_type=benefit_type, status=benefit_status)
    elif role == ROLE_PARENT:
        ParentBenefits.objects.create(parent=target_user.parent, user_origin=origin_user,
                                      benefit_type=benefit_type, status=benefit_status)
    else:
        StudentBenefits.objects.create(student=target_user.student, user_origin=origin_user,
                                       benefit_type=benefit_type, status=benefit_status)


@receiver(post_save, sender=Instructor)
def set_instructor_benefits(sender, instance, created, **kwargs):
    if created and instance.referred_by:
        InstructorBenefits.objects.create(instructor=instance, user_origin=instance.referred_by,
                                          benefit_type=BENEFIT_LESSON, status=BENEFIT_ENABLED)
        set_benefit_to_referrer(instance.referred_by, instance.user, BENEFIT_LESSON, BENEFIT_DISABLED)


@receiver(post_save, sender=Parent)
def set_parent_benefits(sender, instance, created, **kwargs):
    if created and instance.referred_by:
        ParentBenefits.objects.create(parent=instance, user_origin=instance.referred_by,
                                      benefit_type=BENEFIT_LESSON, status=BENEFIT_ENABLED)
        set_benefit_to_referrer(instance.referred_by, instance.user, BENEFIT_LESSON, BENEFIT_DISABLED)


@receiver(post_save, sender=Student)
def set_student_benefits(sender, instance, created, **kwargs):
    if created and instance.referred_by:
        StudentBenefits.objects.create(student=instance, user_origin=instance.referred_by,
                                       benefit_type=BENEFIT_LESSON, status=BENEFIT_ENABLED)
        set_benefit_to_referrer(instance.referred_by, instance.user, BENEFIT_LESSON, BENEFIT_DISABLED)
