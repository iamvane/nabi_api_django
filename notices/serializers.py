from rest_framework import serializers, validators

from .models import Offer


class OfferDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = Offer
        fields = ['name', 'content', 'show_at', 'hide_at']
