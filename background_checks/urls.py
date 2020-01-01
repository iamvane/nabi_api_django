from django.urls import path

from . import views


urlpatterns = [
    path('background-check-request/', views.BackgroundCheckRequestView.as_view(), name='background-checks-request'),
    path('background-check-status/', views.BackgroundCheckView.as_view(), name='background-checks-status'),
]
