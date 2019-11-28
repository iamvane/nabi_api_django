from django.urls import path

from . import views


urlpatterns = [
    path('offers/available/', views.AvailableOfferListView.as_view()),
    path('offers/all/', views.OfferListView.as_view()),
]
