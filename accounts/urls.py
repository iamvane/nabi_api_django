from django.urls import path
from .views import *

urlpatterns = [
    path('register/', CreateAccount.as_view()),
    path('login/', LoginView.as_view()),
    path('reset-password/', ResetPasswordView.as_view()),
    path('set-password/', SetPasswordView.as_view()),
    path('logout/', LogoutView.as_view()),
    path('csrf-token/', CsrfTokenView.as_view()),
    path('whoami/', WhoAmIView.as_view()),
    path('account-info/', UpdateUserInfoView.as_view()),
    path('verify-phone', VerifyPhoneView.as_view()),
    path('build-profile/profile', UpdateProfileView.as_view()),
    path('build-profile/job-preferences', InstructorStep2View.as_view()),
]
