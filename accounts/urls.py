from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.CreateAccount.as_view()),
    path('login/', views.LoginView.as_view()),
    path('forgot-password/', views.ResetPasswordView.as_view()),
    path('logout/', views.LogoutView.as_view()),
    path('csrf-token/', views.CsrfTokenView.as_view()),
    path('whoami/', views.WhoAmIView.as_view()),
    path('fetch-profile/', views.FetchInstructor.as_view()),
    path('account-info/', views.UpdateUserInfoView.as_view()),
    path('verify-phone/', views.VerifyPhoneView.as_view()),
    path('build-profile/', views.UpdateProfileView.as_view()),
    path('build-job-preferences/', views.InstructorBuildJobPreferences.as_view()),
    path('upload_avatar/', views.UploadAvatarView.as_view()),
    path('referral_email/', views.ReferralInvitation.as_view()),
    path('student-details/', views.StudentDetailView.as_view()),
    path('student/<int:pk>/', views.TiedStudentItemView.as_view()),
    path('student/', views.TiedStudentView.as_view()),
    path('education/<int:pk>/', views.InstructorEducationItemView.as_view()),
    path('education/', views.InstructorEducationView.as_view()),
    path('employment/<int:pk>/', views.InstructorEmploymentItemView.as_view()),
    path('employment/', views.InstructorEmploymentView.as_view()),
]
