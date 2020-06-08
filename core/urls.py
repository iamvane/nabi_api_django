from django.urls import path

from . import views


urlpatterns = [
    path('timezones/', views.TimezoneListView.as_view()),
]
