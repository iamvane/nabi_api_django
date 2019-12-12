from django.contrib.auth import get_user_model
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from core.constants import ROLE_INSTRUCTOR

from .models import Availability, Education, Employment, Instructor, InstructorInstruments, InstructorLessonRate, \
    PhoneNumber, get_account

User = get_user_model()


@receiver(pre_save, sender=User)
def set_username(sender, instance, **kwargs):
    if instance.username != instance.email:
        instance.username = instance.email


@receiver(post_save, sender=User)
def set_display_name(sender, instance, **kwargs):
    if kwargs.get('raw', False):   # to don't execute when fixtures are loaded
        return None
    account = get_account(instance)
    if account:
        account.set_display_name()


@receiver(post_save, sender=Availability)
@receiver(post_save, sender=Education)
@receiver(post_save, sender=Employment)
@receiver(post_save, sender=InstructorInstruments)
@receiver(post_save, sender=InstructorLessonRate)
@receiver(post_save, sender=PhoneNumber)
@receiver(post_save, sender=Instructor)
@receiver(post_save, sender=User)
def change_completed_profile(sender, instance, **kwargs):
    """Call method to update value of completed property"""
    if kwargs.get('raw', False):   # to don't execute when fixtures are loaded
        return None
    if isinstance(instance, Instructor):
        instance.update_completed()
    if isinstance(instance, User) and instance.get_role() == ROLE_INSTRUCTOR:
        instance.instructor.update_completed()
    if isinstance(instance, PhoneNumber) and instance.user.get_role == ROLE_INSTRUCTOR:
        instance.user.instructor.update_completed()
    if isinstance(instance, InstructorInstruments) or isinstance(instance, InstructorLessonRate) \
            or isinstance(instance, Availability) or isinstance(instance, Education) \
            or isinstance(instance, Employment):
        instance.instructor.update_completed()
