web: gunicorn --pythonpath nabi_api_django nabi_api_django.production --log-file -
worker: celery -A nabi_api_django.celery_config worker -l info
