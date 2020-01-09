from django.urls import path

from . import views


urlpatterns = [
    path('lesson-request/', views.LessonRequestView.as_view()),
    path('lesson-request/<int:pk>/', views.LessonRequestItemView.as_view()),
    path('applications/', views.ApplicationView.as_view()),
    path('lesson-request-list/', views.LessonRequestListView.as_view()),
    path('lesson-request-item/<int:pk>/', views.LessonRequestItemListView.as_view()),
    path('lesson-request-list/', views.LessonRequestList.as_view()),
    path('application-list/<int:lesson_req_id>/', views.ApplicationListView.as_view()),
]
