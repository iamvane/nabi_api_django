from django.contrib.auth import get_user_model
from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import Lesson


@receiver(pre_save, sender=Lesson)
def set_students_details(sender, instance, raw, using, update_fields, **kwargs):
    if raw:  # to don't execute when fixtures are loaded
        return None
    elif instance.id is None:   # Lesson creation
        if instance.booking.user.is_parent():
            instance.student_details = [{'name': student.name, 'age': student.age}
                                        for student in instance.booking.application.request.students.all()]
        else:
            instance.student_details = [{'name': instance.booking.user.first_name,
                                         'age': instance.booking.user.student.age}]
