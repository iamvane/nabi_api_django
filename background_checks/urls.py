from django.urls import path

from . import views


urlpatterns = [
    path('background-checks-request/', views.BackgroundCheckRequestView.as_view(), name='background-checks-request'),
    path('background-checks-status/', views.BackgroundCheckView.as_view(), name='background-checks-status'),
]
