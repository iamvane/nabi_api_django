from django.contrib.auth import get_user_model
from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import Lesson, LessonBooking


# @receiver(pre_save, sender=LessonBooking)
# def set_instructor_rate(sender, instance, raw, using, update_fields, **kwargs):
#     if raw:  # to don't execute when fixtures are loaded
#         return None
#     elif instance.id is None:   # LessonBooking creation
#         if instance.application:
#             instance.instructor = instance.application.instructor
#             instance.rate = instance.application.rate
#     else:
#         existing_instance = LessonBooking.objects.get(id=instance.id)
#         if existing_instance.application != instance.application:
#             if instance.application:
#                 instance.instructor = instance.application.instructor
#                 instance.rate = instance.application.rate
#             else:
#                 instance.instructor = None
#                 instance.rate = None
#     if instance.application is None and instance.request is None:
#         raise ValueError('You must link it to request or application')
#     if (instance.request is not None) and (instance.request.user != instance.user):
#         raise ValueError('Wrong selected user')
#     if (instance.application is not None) and (instance.application.request.user != instance.user):
#         raise ValueError('Wrong selected user')


# @receiver(pre_save, sender=Lesson)
# def set_students_details(sender, instance, raw, using, update_fields, **kwargs):
#     if raw:  # to don't execute when fixtures are loaded
#         return None
#     elif instance.id is None:   # Lesson creation
#         if instance.booking:
#             instance.instructor = instance.booking.instructor
#             instance.rate = instance.booking.rate
#             if instance.booking.user.is_parent():
#                 if instance.booking.application:
#                     instance.student_details = [{'name': student.name, 'age': student.age}
#                                                 for student in instance.booking.application.request.students.all()]
#                 else:
#                     instance.student_details = [{'name': student.name, 'age': student.age}
#                                                 for student in instance.booking.request.students.all()]
#             else:
#                 instance.student_details = [{'name': instance.booking.user.first_name,
#                                              'age': instance.booking.user.student.age}]
