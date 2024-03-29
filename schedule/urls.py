from django.urls import path

from . import views

app_name = 'schedule'


urlpatterns = [
    path('availability/', views.Availability.as_view(), name='availability'),
    path('schedule/', views.Schedule.as_view(), name='schedule'),
]
