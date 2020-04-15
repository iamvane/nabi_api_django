import stripe

from django.conf import settings
from rest_framework import serializers

from .models import UserPaymentMethod

stripe.api_key = settings.STRIPE_SECRET_KEY


class GetPaymentMethodSerializer(serializers.ModelSerializer):
    details = serializers.SerializerMethodField()

    class Meta:
        model = UserPaymentMethod
        fields = ('id', 'is_main')

    def get_details(self, instance):
        pm_data = stripe.PaymentMethod.retrieve(instance.stripe_payment_method_id)
        return {'brand': pm_data.get('card', {}).get('brand', ''),
                'expiration_date': f"{pm_data.get('card', {}).get('exp_month', '')}/{pm_data.get('card', {}).get('exp_month', '')}",
                'last_4digits': pm_data.get('card', {}).get('last4'),
                }
