from django.urls import path

from . import views

app_name = 'references'

urlpatterns = [
    path('request-references/', views.RegisterRequestReferenceView.as_view()),
]
