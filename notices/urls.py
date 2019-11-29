from django.urls import path

from . import views


urlpatterns = [
    path('offers-active/', views.AvailableOfferListView.as_view()),
    path('offers/', views.OfferListView.as_view()),
]
