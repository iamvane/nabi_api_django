# Nabi API Django

Example local_settings.py:

```python
import os

DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ.get('DB_NAME', 'nabidb'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASS', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': '5432',
        'OPTIONS': {},
        'TEST': {
            'NAME': 'nabidb_test',
        },
    }
}

ALLOWED_HOSTS = ['*']

INTERNAL_IPS = ['127.0.0.1']

CORS_ORIGIN_WHITELIST = ['http://*']

AUTH_PASSWORD_VALIDATORS = []

STATIC_URL = '/dj-static/'

MEDIA_URL = '/dj-media/'

```
