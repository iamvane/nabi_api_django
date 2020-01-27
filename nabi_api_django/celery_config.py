import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nabi_api_django.production')

app = Celery('my_tasks')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
