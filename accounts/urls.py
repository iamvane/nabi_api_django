from django.urls import path
from .views import *

urlpatterns = [
    path('register', CreateAccount.as_view()),
]
