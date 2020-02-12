from django.urls import path

from . import views


urlpatterns = [
    path('lesson-request/', views.LessonRequestView.as_view(), name='lesson_request'),
    path('lesson-request/<int:pk>/', views.LessonRequestItemView.as_view()),
    path('applications/', views.ApplicationView.as_view()),
    path('lesson-request-list/', views.LessonRequestListView.as_view()),
    path('lesson-request-item/<int:pk>/', views.LessonRequestItemListView.as_view(), name='lesson_request_item'),
    path('application-list/<int:lesson_req_id>/', views.ApplicationListView.as_view()),
    path('booking-lessons/', views.LessonBookingRegisterView.as_view()),
    path('application-data/<int:app_id>/', views.ApplicationDataView.as_view()),
    path('lesson-grade/', views.GradeLessonView.as_view()),
]
