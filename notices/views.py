from rest_framework import status, views
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Offer
from .serializers import OfferDetailSerializer


class AvailableOfferListView(views.APIView):
    """Get a list of available offers (which should be displayed today)"""
    permission_classes = (AllowAny, )

    def get(self, request):
        serializer = OfferDetailSerializer(Offer.get_last_active_offer())
        return Response(serializer.data, status=status.HTTP_200_OK)


class OfferListView(views.APIView):
    """Get a list of all offers"""
    permission_classes = (AllowAny,)

    def get(self, request):
        serializer = OfferDetailSerializer(Offer.objects.order_by('show_at'), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
