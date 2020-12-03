from rest_framework import serializers

from .models import Offer


class OfferDetailSerializer(serializers.ModelSerializer):
    freeLesson = serializers.BooleanField(source='free_lesson')
    hideAt = serializers.DateTimeField(source='hide_at', format='%Y-%m-%d %H:%M:%S')
    percentDiscount = serializers.IntegerField(source='percent_discount')
    showAt = serializers.DateTimeField(source='show_at', format='%Y-%m-%d %H:%M:%S')

    class Meta:
        model = Offer
        fields = ['content', 'freeLesson', 'hideAt',  'name', 'percentDiscount', 'showAt']
