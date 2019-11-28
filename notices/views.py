from django.utils import timezone

from rest_framework import status, views
from rest_framework.response import Response

from .models import Offer
from .serializers import OfferDetailSerializer, OfferSerializer


class AvailableOfferListView(views.APIView):
    """Get a list of available offers (which should be displayed today)"""

    def get(self, request):
        today = timezone.now()
        qs = Offer.objects.filter(show_at__lte=today).exclude(hide_at__lte=today).order_by('name')
        serializer = OfferSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OfferListView(views.APIView):
    """Get a list of all offers"""

    def get(self, request):
        serializer = OfferDetailSerializer(Offer.objects.order_by('show_at'), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
