import requests

from django.conf import settings
from django.contrib.auth import get_user_model

from core.utils import send_admin_email
from nabi_api_django.celery_config import app

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
