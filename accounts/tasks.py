from django.contrib.auth import get_user_model

from core.models import TaskLog
from core.utils import send_admin_email
from nabi_api_django.celery_config import app

from .models import InstructorReview
from .utils import send_instructor_info_review

User = get_user_model()


@app.task
def alert_user_without_location_coordinates():
    """Send an email to administrator, to indicate what users has not location or coordinates"""
    for user in User.objects.all():
        if user.is_superuser:
            continue
        elif user.is_instructor():
            account = user.instructor
            role = 'instructor'
        elif user.is_parent():
            account = user.parent
            role = 'parent'
        elif user.is_student():
            account = user.student
            role = 'student'
        else:
            account = None
        if account:
            if not account.coordinates:
                if account.location:
                    send_admin_email(f"{role.capitalize()} without coordinates",
                                     f"""The {role} {user.email} (id {account.id}) has not coordinates, 
                                     but has stored location {account.location}.""")
                else:
                    send_admin_email(f"{role.capitalize()} without coordinates",
                                     f"The instructor {user.email} (id {account.id}) has not coordinates.")
            elif not account.location:
                send_admin_email(f"{role.capitalize()} without location",
                                 f"""The {role} {user.email} (id {account.id}) has coordinates (lat: {account.coordinates.coords[1]}  long: {account.coordinates.coords[0]}), 
                                 but has not location stored.""")


@app.task
def info_instructor_review(obj_id, task_log_id):
    try:
        instructor_review = InstructorReview.objects.get(id=obj_id)
    except InstructorReview.DoesNotExist:
        send_admin_email(
            'Error executing info_instructor_review task',
            f'Executing task info_instructor_review (params: instructor_id {obj_id}) '
            f'InstructorReview DoesNotExist error was raised'
        )
    send_instructor_info_review(instructor_review)
    TaskLog.objects.filter(id=task_log_id).delete()
