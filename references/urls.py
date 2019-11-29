from django.urls import path

from . import views


urlpatterns = [
    path('request-references/register/', views.RegisterRequestReferenceView.as_view()),
]
