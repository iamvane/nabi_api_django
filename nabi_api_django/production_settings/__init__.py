from nabi_api_django.settings import *

DEBUG = False
TEMPLATE_DEBUG = False

ALLOWED_HOSTS = [
    'localhost',
    '.herokuapp.com'
]


TWILIO_SERVICE_SID = os.environ['TWILIO_SERVICE_SID']
TWILIO_ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
TWILIO_AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']


SENDGRID_API_KEY = os.environ['SENDGRID_KEY']
EMAIL_HOST_PASSWORD = SENDGRID_API_KEY

DEFAULT_FROM_EMAIL = os.environ['DEFAULT_FROM_EMAIL']
