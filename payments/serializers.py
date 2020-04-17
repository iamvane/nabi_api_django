import stripe

from django.conf import settings
from rest_framework import serializers

from .models import UserPaymentMethod

stripe.api_key = settings.STRIPE_SECRET_KEY


class GetPaymentMethodSerializer(serializers.ModelSerializer):
    details = serializers.SerializerMethodField()

    class Meta:
        model = UserPaymentMethod
        fields = ('id', 'is_main', 'details')

    def get_details(self, instance):
        pm_data = stripe.PaymentMethod.retrieve(instance.stripe_payment_method_id)
        if pm_data.get('card', {}).get('exp_month') is not None and pm_data.get('card', {}).get('exp_year') is not None:
            if pm_data.get('card', {}).get('exp_month') < 10:
                exp_date = f"0{pm_data.get('card', {}).get('exp_month')}/{pm_data.get('card', {}).get('exp_year')}"
            else:
                exp_date = f"{pm_data.get('card', {}).get('exp_month')}/{pm_data.get('card', {}).get('exp_year')}"
        else:
            exp_date = ''
        return {'brand': pm_data.get('card', {}).get('brand', ''),
                'expiration_date': exp_date,
                'last_4digits': pm_data.get('card', {}).get('last4', ''),
                }
