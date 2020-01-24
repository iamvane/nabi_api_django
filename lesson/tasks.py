from django.contrib.gis.measure import D

from accounts.models import get_account, Instructor
from core.models import TaskLog
from nabi_api_django.celery_config import app

from .models import LessonRequest
from .utils import send_alert_request_instructor


@app.task
def send_request_alert_instructors(request_id, task_log_id):
    """Send an email to instructors in a place near to 50 miles from lesson request location"""
    request = LessonRequest.objects.get(id=request_id)
    account = get_account(request.user)
    if account and account.coordinates:
        for instructor in Instructor.objects.filter(coordinates__distance_lte=(account.coordinates, D(mi=50))):
            send_alert_request_instructor(instructor, request, account)
    TaskLog.objects.filter(id=task_log_id).delete()
