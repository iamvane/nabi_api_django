from django.urls import path
from .views import *

urlpatterns = [
    path('register', CreateAccount.as_view()),
    path('login', LoginView.as_view()),
    path('csrf-token', CsrfTokenView.as_view()),
    path('whoami', WhoAmIView.as_view()),
    path('build-profile', CreateAccountInfoView.as_view()),
    path('verify-phone', VerifyPhoneView.as_view()),
]
