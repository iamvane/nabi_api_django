from django.urls import path

from . import views


urlpatterns = [
    path('request-references/', views.RegisterRequestReferenceView.as_view()),
]
