from django.urls import path

from rest_framework_simplejwt import views as jwt_views

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
    path('referral-email/', views.ReferralInvitation.as_view()),
    path('student-details/', views.StudentDetailView.as_view()),
    path('students/<int:pk>/', views.TiedStudentItemView.as_view()),
    path('students/', views.TiedStudentView.as_view()),
    path('education/<int:pk>/', views.InstructorEducationItemView.as_view()),
    path('education/', views.InstructorEducationView.as_view()),
    path('employment/<int:pk>/', views.InstructorEmploymentItemView.as_view()),
    path('employment/', views.InstructorEmploymentView.as_view()),
    path('api-token/', jwt_views.TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api-token-refresh/', jwt_views.TokenRefreshView.as_view(), name='token_refresh'),
    path('instructors/', views.InstructorListView.as_view()),
    path('instructors/<int:pk>/', views.InstructorDetailView.as_view()),
    path('minimal-rate/', views.MinimalLessonRateView.as_view()),
    path('registration-affiliate/', views.AffiliateRegisterView.as_view()),
    path('dashboard/', views.DashboardView.as_view()),
    path('referral-info/<str:token>/', views.ReferralInfoView.as_view()),
    path('referral-dashboard/', views.ReferralDashboardView.as_view()),
    path('upload-video-profile/', views.UploadVideoProfileView.as_view()),
    path('sign-file/', views.S3SignatureFile.as_view()),
]
