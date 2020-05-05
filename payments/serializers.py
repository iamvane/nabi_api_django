from rest_framework import serializers


class GetPaymentMethodSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=200)
    brand = serializers.CharField(max_length=50)
    expirationDate = serializers.CharField(max_length=10)
    last4Digits = serializers.CharField(max_length=4)

    def to_internal_value(self, data):
        new_data = {}
        new_data['code'] = data.get('id')
        new_data['brand'] = data.get('card', {}).get('brand', '')
        new_data['last4Digits'] = data.get('card', {}).get('last4', '')
        month = data.get('card', {}).get('exp_month', '')
        year = data.get('card', {}).get('exp_year', '')
        if year and month:
            if int(month) < 10:
                new_data['expirationDate'] = f'0{month}/{year}'
            else:
                new_data['expirationDate'] = f'{month}/{year}'
        return new_data
