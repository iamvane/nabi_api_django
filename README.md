# Nabi API Django

APIs for Nabi Music project

### Required software:
Python 3.7.*
PostgreSQL
Postgis
Docker and Docker Compose

### To make run in local environment
1. Create a database (default name is **nabidb**) and execute `CREATE EXTENSION postgis; CREATE EXTENSION hstore;`
2. Create a virtual environment and activate it
3. Install packages with `pip install -r requirements.txt`
4. Copy **nabi_api_django/env.example** to **.env**. Update values in **.env** file (this file is skipped by git)
To generate a secret key, execute: `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`
5. Create a **nabi_api_django/local_settings.py** file including following keys (see **staging_settings.py** as example): SIMPLE_JWT, DEFAULT_FROM_EMAIL, ADMIN_EMAIL, SENDGRID_CONTACT_LIST_IDS, SENDGRID_EMAIL_TEMPLATES, HUBSPOT_CONTACT_LIST_IDS, HUBSPOT_TEMPLATE_IDS, AWS_S3_USAGE
6. Run RabbitMQ container using provided **docker-compose.yml** file with `docker-compose up -d` (can be shut down with `docker-compose down`)
7. Apply migrations with `python manage.py migrate`
8. Finally, to run backend project execute `python manage.py runserver`

### Run celery worker
A request for execute a task is received by RabbitMQ container, and store it; for execution of these task, a worker should be executed.
To run a worker: `celery worker -A nabi_api_django.celery_config -B -l info`
Note: `-B` option allow to execute scheduled tasks
