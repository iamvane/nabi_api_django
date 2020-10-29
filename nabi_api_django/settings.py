import dotenv
import os
import warnings

with warnings.catch_warnings():   # To avoid warning when .env file does not exists
    warnings.simplefilter('ignore')
    dotenv.read_dotenv()

ENVIRON_TYPE = os.environ['ENVIRONMENT']
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ['SECRET_KEY']
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(os.environ['DEBUG'])

ALLOWED_HOSTS = []

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'django.contrib.gis',
    'rest_framework',

    'core.apps.CoreConfig',
    'accounts.apps.AccountsConfig',
    'payments.apps.PaymentsConfig',
    'lesson.apps.LessonConfig',
    'notices',
    'references.apps.ReferencesConfig',
    'background_checks.apps.BackgroundChecksConfig',
    'schedule',

    'drf_yasg',
    'corsheaders',
    'storages',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'nabi_api_django.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'nabi_api_django.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': os.environ.get('DB_NAME', 'nabidb'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASS'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'OPTIONS': {'sslmode': 'require'},
        'TEST': {
            'NAME': 'nabidb_test',
        },
    }
}

AUTH_USER_MODEL = 'core.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

HOSTNAME_PROTOCOL = os.environ['HOSTNAME_PROTOCOL']

EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.sendgrid.net')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'apikey')
EMAIL_HOST_PASSWORD = os.environ['EMAIL_HOST_PASSWORD']
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))


# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/New_York'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = '/dj-static/'

# Absolute filesystem path to the directory that will hold user-uploaded files.
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/dj-media/'


# # # REST Framework # # #
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': int(os.environ.get('REST_PAGE_SIZE', 20)),
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S'
}


# # # Celery configuration # # #
CELERY_BROKER_URL = os.environ['BROKER_URL']
BROKER_POOL_LIMIT = 1


# # # Third-party services # # #
GOOGLE_MAPS_API_KEY = os.environ['GOOGLE_MAPS_API_KEY']

TWILIO_SERVICE_SID = os.environ['TWILIO_SERVICE_SID']
TWILIO_ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
TWILIO_AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']
TWILIO_FROM_NUMBER = os.environ['TWILIO_FROM_NUMBER']

STRIPE_PUBLIC_KEY = os.environ['STRIPE_PUBLIC_KEY']
STRIPE_SECRET_KEY = os.environ['STRIPE_SECRET_KEY']

ACCURATE_CLIENT_ID = os.environ['ACCURATE_CLIENT_ID']
ACCURATE_CLIENT_SECRET = os.environ['ACCURATE_CLIENT_SECRET']
ACCURATE_PLAN_PARAMETER = 'PKG_STANDARD'
ACCURATE_PLAN_ADDITIONALS = ['SON', ]

GOOGLE_FORM_REFERENCES_URL = 'https://forms.gle/my-custom-form'

SENDGRID_API_BASE_URL = 'https://api.sendgrid.com/v3/'

HUBSPOT_API_KEY = os.environ['HUBSPOT_API_KEY']


# # # Environment specific settings # # #
if ENVIRON_TYPE == 'production':
    try:
        from .production_settings import *
    except Exception as e:
        print('Error importing production_settings.py: {}'.format(str(e)))
elif ENVIRON_TYPE == 'staging':
    try:
        from .staging_settings import *
    except Exception as e:
        print('Error importing staging_settings.py: {}'.format(str(e)))
else:
    from .local_settings import *
