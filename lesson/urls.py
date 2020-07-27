from django.urls import path

from . import views


urlpatterns = [
    path('lesson-request/', views.LessonRequestView.as_view(), name='lesson_request'),
    path('lesson-request/<int:pk>/', views.LessonRequestItemView.as_view()),
    path('applications/', views.ApplicationView.as_view()),
    path('lesson-request-list/', views.LessonRequestListView.as_view()),
    path('lesson-request-item/<int:pk>/', views.LessonRequestItemListView.as_view(), name='lesson_request_item'),
    path('application-list/<int:lesson_req_id>/', views.ApplicationListView.as_view()),
    path('booking-data/<int:student_id>/', views.AmountsForBookingView.as_view()),
    path('confirm-booking/', views.LessonBookingRegisterView.as_view()),
    path('lessons/', views.LessonCreateView.as_view()),
    path('lessons/<int:lesson_id>/', views.LessonView.as_view()),
]
