from django.urls import path

from . import views


urlpatterns = [
    path('lesson-request/', views.LessonRequestView.as_view()),
    path('lesson-request/<int:pk>/', views.LessonRequestItemView.as_view()),
    path('applications/', views.ApplicationView.as_view()),
]
